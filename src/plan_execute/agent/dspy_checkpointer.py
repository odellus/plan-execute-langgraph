"""
Custom conversation persistence checkpointer for DSPy.
This replaces LangGraph's PostgreSQL checkpointer with a DSPy-compatible solution.
"""
import json
import logging
from typing import Dict, List, Any, Optional
from psycopg_pool import AsyncConnectionPool
import dspy

logger = logging.getLogger("dspy_checkpointer")


class DSPyConversationCheckpointer:
    """
    Custom checkpointer for DSPy conversations using PostgreSQL.
    Stores and retrieves conversation history for thread-based persistence.
    """
    
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool
        
    async def setup(self):
        """Initialize the database tables for conversation storage."""
        async with self.pool.connection() as conn:
            # Create table for storing conversation history
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS dspy_conversations (
                    thread_id TEXT PRIMARY KEY,
                    history JSONB NOT NULL DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index for faster lookups
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_dspy_conversations_thread_id 
                ON dspy_conversations(thread_id)
            """)
            
            # Create index for updated_at for cleanup queries
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_dspy_conversations_updated_at 
                ON dspy_conversations(updated_at)
            """)
            
            logger.info("DSPy conversation checkpointer initialized")
    
    async def save_conversation(self, thread_id: str, history: dspy.History):
        """
        Save conversation history to PostgreSQL.
        
        Args:
            thread_id: Unique identifier for the conversation thread
            history: DSPy History object containing conversation messages
        """
        try:
            # Convert DSPy History to JSON-serializable format
            history_data = []
            if history and hasattr(history, 'messages') and history.messages:
                history_data = history.messages
            
            async with self.pool.connection() as conn:
                # Use upsert to insert or update
                await conn.execute("""
                    INSERT INTO dspy_conversations (thread_id, history, updated_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (thread_id) 
                    DO UPDATE SET 
                        history = EXCLUDED.history,
                        updated_at = CURRENT_TIMESTAMP
                """, (thread_id, json.dumps(history_data)))
                
                logger.info(f"Saved conversation for thread {thread_id} with {len(history_data)} messages")
                
        except Exception as e:
            logger.error(f"Failed to save conversation for thread {thread_id}: {e}")
            raise
    
    async def load_conversation(self, thread_id: str) -> dspy.History:
        """
        Load conversation history from PostgreSQL.
        
        Args:
            thread_id: Unique identifier for the conversation thread
            
        Returns:
            DSPy History object with loaded conversation messages
        """
        try:
            async with self.pool.connection() as conn:
                cursor = await conn.execute("""
                    SELECT history FROM dspy_conversations 
                    WHERE thread_id = %s
                """, (thread_id,))
                
                row = await cursor.fetchone()
                
                if row and row[0]:
                    history_data = row[0]  # JSONB is automatically parsed
                    logger.info(f"Loaded conversation for thread {thread_id} with {len(history_data)} messages")
                    return dspy.History(messages=history_data)
                else:
                    logger.info(f"No existing conversation found for thread {thread_id}")
                    return dspy.History(messages=[])
                    
        except Exception as e:
            logger.error(f"Failed to load conversation for thread {thread_id}: {e}")
            # Return empty history on error to allow conversation to continue
            return dspy.History(messages=[])
    
    async def delete_conversation(self, thread_id: str):
        """
        Delete conversation history for a specific thread.
        
        Args:
            thread_id: Unique identifier for the conversation thread
        """
        try:
            async with self.pool.connection() as conn:
                await conn.execute("""
                    DELETE FROM dspy_conversations 
                    WHERE thread_id = %s
                """, (thread_id,))
                
                logger.info(f"Deleted conversation for thread {thread_id}")
                
        except Exception as e:
            logger.error(f"Failed to delete conversation for thread {thread_id}: {e}")
            raise
    
    async def list_conversations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List recent conversations.
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation metadata
        """
        try:
            async with self.pool.connection() as conn:
                cursor = await conn.execute("""
                    SELECT thread_id, 
                           jsonb_array_length(history) as message_count,
                           created_at, 
                           updated_at
                    FROM dspy_conversations 
                    ORDER BY updated_at DESC 
                    LIMIT %s
                """, (limit,))
                
                conversations = []
                async for row in cursor:
                    conversations.append({
                        'thread_id': row[0],
                        'message_count': row[1] or 0,
                        'created_at': row[2],
                        'updated_at': row[3]
                    })
                
                return conversations
                
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            return []
    
    async def cleanup_old_conversations(self, days_old: int = 30):
        """
        Clean up old conversations to prevent database bloat.
        
        Args:
            days_old: Delete conversations older than this many days
        """
        try:
            async with self.pool.connection() as conn:
                await conn.execute("""
                    DELETE FROM dspy_conversations 
                    WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
                """, (days_old,))
                
                logger.info(f"Cleaned up old conversations (older than {days_old} days)")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old conversations: {e}")
            raise