#!/bin/bash
# Start mock MCP servers for local development

set -e

echo "Starting Mock MCP Servers..."

# Create logs directory
mkdir -p logs

# Start database server
echo "Starting Database Server..."
python src/examples/mock_servers/database_server.py > logs/database_server.log 2>&1 &
DATABASE_PID=$!
echo "Database Server started (PID: $DATABASE_PID)"

# Start filesystem server
echo "Starting Filesystem Server..."
python src/examples/mock_servers/filesystem_server.py > logs/filesystem_server.log 2>&1 &
FILESYSTEM_PID=$!
echo "Filesystem Server started (PID: $FILESYSTEM_PID)"

# Start API server
echo "Starting API Server..."
python src/examples/mock_servers/api_server.py > logs/api_server.log 2>&1 &
API_PID=$!
echo "API Server started (PID: $API_PID)"

# Save PIDs to file
echo "$DATABASE_PID" > logs/database_server.pid
echo "$FILESYSTEM_PID" > logs/filesystem_server.pid
echo "$API_PID" > logs/api_server.pid

echo ""
echo "All mock servers started successfully!"
echo "Database Server PID: $DATABASE_PID"
echo "Filesystem Server PID: $FILESYSTEM_PID"
echo "API Server PID: $API_PID"
echo ""
echo "To stop servers, run: ./scripts/stop_mock_servers.sh"
