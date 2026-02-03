#!/bin/bash

# Kill any existing port-forwards to avoid conflicts
pkill -f "kubectl port-forward"

echo "Starting port forwarding for RefMap services..."

# Forward each service in the background
kubectl port-forward svc/climate-impact 4001:4001 > /dev/null 2>&1 &
kubectl port-forward svc/wind-assessment 4002:4002 > /dev/null 2>&1 &
kubectl port-forward svc/noise-assessment 4003:4003 > /dev/null 2>&1 &
kubectl port-forward svc/optimized-trajectories 4004:4004 > /dev/null 2>&1 &
kubectl port-forward svc/emissions 4005:4005 > /dev/null 2>&1 &
kubectl port-forward svc/atmospheric-pollution 4006:4006 > /dev/null 2>&1 &

echo "✅ Port forwarding active!"
echo "Services are now accessible at http://localhost:4001 through 4006"
echo "Press Ctrl+C to stop (if run in foreground) or kill the processes later."
