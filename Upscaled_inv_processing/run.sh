#!/bin/bash

# Inventory Processing CLI - Quick Start Script

echo "🏭 Inventory Processing System"
echo "==============================="
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Check if dist exists
if [ ! -d "dist" ]; then
    echo "🔨 Building project..."
    npm run build
    echo ""
fi

# Run the application
echo "🚀 Starting inventory processor..."
echo ""
npm start
