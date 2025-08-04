-- Create the application database (only if it does not yet exist)
SELECT 'CREATE DATABASE langgraph'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'langgraph')\gexec