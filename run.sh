#!/bin/bash

case "$1" in
    start)
        echo "🚀 Starting PX4 Demo Stack..."
        docker compose up -d
        echo ""
        echo "✅ PX4 + Gazebo starting..."
        echo "✅ ROS 2 Bridge starting..."
        echo ""
        echo "To see logs: docker compose logs -f"
        echo "To enter ROS 2: docker exec -it ros2-bridge bash"
        ;;
    stop)
        echo "🛑 Stopping PX4 Demo Stack..."
        docker compose down
        ;;
    status)
        docker compose ps
        ;;
    logs)
        docker compose logs -f
        ;;
    shell)
        docker exec -it ros2-bridge bash
        ;;
    test)
        docker exec -it ros2-bridge bash -c "
            source /opt/ros/humble/setup.bash
            source /root/px4_ros_com/install/setup.bash
            echo '📡 Testing connection...'
            ros2 topic list | grep '/fmu' && echo '✅ Connection successful!' || echo '❌ No topics found. Is PX4 running?'
        "
        ;;
    *)
        echo "Usage: $0 {start|stop|status|logs|shell|test}"
        exit 1
esac
