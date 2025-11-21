#!/bin/bash

# Quick Stress Test Script
# Run different test scenarios easily

set -e

API_URL="${API_URL:-http://localhost:2014}"
EVENT_LINK="${1:-}"

if [ -z "$EVENT_LINK" ]; then
    echo "❌ Error: Event link required"
    echo "Usage: ./quick_test.sh <event_link> [test_type]"
    echo ""
    echo "Test types:"
    echo "  small   - 50 users, 30 seconds"
    echo "  medium  - 100 users, 60 seconds"
    echo "  large   - 200 users, 120 seconds"
    echo "  extreme - 500 users, 60 seconds"
    echo "  ramp    - Ramp up to 200 users"
    echo ""
    echo "Example: ./quick_test.sh abc-123-def medium"
    exit 1
fi

TEST_TYPE="${2:-medium}"

echo "🚀 Running $TEST_TYPE test..."
echo "📡 API: $API_URL"
echo "🔗 Event: $EVENT_LINK"
echo ""

case $TEST_TYPE in
    small)
        echo "📊 Test: 50 concurrent users, 30 seconds"
        python3 stress_test.py \
            --api "$API_URL" \
            --link "$EVENT_LINK" \
            --users 50 \
            --duration 30 \
            --batch-size 25
        ;;

    medium)
        echo "📊 Test: 100 concurrent users, 60 seconds"
        python3 stress_test.py \
            --api "$API_URL" \
            --link "$EVENT_LINK" \
            --users 100 \
            --duration 60 \
            --batch-size 50
        ;;

    large)
        echo "📊 Test: 200 concurrent users, 120 seconds"
        python3 stress_test.py \
            --api "$API_URL" \
            --link "$EVENT_LINK" \
            --users 200 \
            --duration 120 \
            --batch-size 50
        ;;

    extreme)
        echo "📊 Test: 500 concurrent users, 60 seconds (EXTREME!)"
        echo "⚠️  This may fail with current single-worker setup"
        python3 stress_test.py \
            --api "$API_URL" \
            --link "$EVENT_LINK" \
            --users 500 \
            --duration 60 \
            --batch-size 50
        ;;

    ramp)
        echo "📊 Test: Ramp up to 200 users over 60s, hold 120s"
        python3 stress_test.py \
            --api "$API_URL" \
            --link "$EVENT_LINK" \
            --mode ramp \
            --max-users 200 \
            --ramp-time 60 \
            --hold-time 120
        ;;

    vote)
        echo "📊 Test: 100 users with voting enabled"
        python3 stress_test.py \
            --api "$API_URL" \
            --link "$EVENT_LINK" \
            --users 100 \
            --duration 60 \
            --batch-size 50 \
            --vote
        ;;

    *)
        echo "❌ Unknown test type: $TEST_TYPE"
        echo "Valid types: small, medium, large, extreme, ramp, vote"
        exit 1
        ;;
esac

echo ""
echo "✅ Test completed!"
