#!/bin/bash

# Simple HTTP Service Checker

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check if URL argument was provided
if [ -z "$1" ]; then
    echo "Usage: $0 <URL>"
    echo "Example: $0 https://google.com"
    exit 1
fi

URL="$1"
LOG_FILE="$(dirname "$0")/monitor.log"

# Query URL with a 5-second timeout and get HTTP code and response time
RESULT=$(curl -s -o /dev/null -w "%{http_code} %{time_total}" --max-time 5 "$URL")
HTTP_CODE=$(echo "$RESULT" | cut -d ' ' -f 1)
RESPONSE_TIME=$(echo "$RESULT" | cut -d ' ' -f 2)

# Determine service availability based on HTTP status code
if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
    STATUS="${GREEN}ONLINE (OK)${NC}"
elif [ "$HTTP_CODE" -ge 300 ] && [ "$HTTP_CODE" -lt 400 ]; then
    STATUS="${YELLOW}REDIRECT ($HTTP_CODE)${NC}"
elif [ "$HTTP_CODE" -eq 000 ]; then
    STATUS="${RED}SERVER DOWN / UNREACHABLE${NC}"
else
    STATUS="${RED}ERROR ($HTTP_CODE)${NC}"
fi

# Print report to screen
echo "----------------------------------------"
echo "Server:        $URL"
echo "HTTP Status:   $HTTP_CODE"
echo "Response Time: ${RESPONSE_TIME}s"
echo -e "Result:        $STATUS"
echo "----------------------------------------"

# Save record to log file
echo "$(date '+%Y-%m-%d %H:%M:%S') | $URL | HTTP: $HTTP_CODE | ${RESPONSE_TIME}s" >> "$LOG_FILE"
