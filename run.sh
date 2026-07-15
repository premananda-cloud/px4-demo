#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

case "$1" in
    start)
        echo -e "${GREEN}🚀 Starting PX4 Demo Stack...${NC}"

        # Build images if they don't exist
        if ! docker image inspect px4-demo:latest &>/dev/null; then
            echo -e "${YELLOW}Building PX4 image...${NC}"
            docker compose build px4-gazebo
        fi

        if ! docker image inspect ros2-bridge:latest &>/dev/null; then
            echo -e "${YELLOW}Building ROS 2 image...${NC}"
            docker compose build ros2-bridge
        fi

        # Allow X11 connections
        xhost +local:docker 2>/dev/null || true

        # Start services
        docker compose up -d

        echo -e "${GREEN}✅ All services started!${NC}"
        echo ""
        echo -e "${YELLOW}📊 Status:${NC}"
        docker compose ps
        echo ""
        echo -e "${YELLOW}📝 Commands:${NC}"
        echo "  View logs:    docker compose logs -f"
        echo "  Enter ROS 2:  docker exec -it ros2-bridge bash"
        echo "  Enter PX4:    docker exec -it px4-demo bash"
        echo "  Test bridge:  ./run.sh test"
        echo "  Stop:         ./run.sh stop"
        ;;

    stop)
        echo -e "${RED}🛑 Stopping PX4 Demo Stack...${NC}"
        docker compose down
        echo -e "${GREEN}✅ All services stopped${NC}"
        ;;

    restart)
        $0 stop
        $0 start
        ;;

    status)
        docker compose ps
        ;;

    logs)
        docker compose logs -f --tail=100
        ;;

    shell)
        if [ -z "$2" ]; then
            echo -e "${YELLOW}Usage: $0 shell {px4-gazebo|ros2-bridge}${NC}"
            exit 1
        fi
        docker exec -it "$2" bash
        ;;

    test)
        echo -e "${YELLOW}📡 Testing ROS 2 bridge...${NC}"
        docker exec -it ros2-bridge bash -c "
            source /opt/ros/humble/setup.bash
            source /root/colcon_ws/install/setup.bash
            echo ''
            echo '📋 Available PX4 topics:'
            ros2 topic list 2>/dev/null | grep '/fmu' | head -10
            echo '...'
            echo ''
            echo '📊 Reading vehicle attitude (once):'
            ros2 topic echo /fmu/out/vehicle_attitude --once --field q
        "
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Connection successful!${NC}"
        else
            echo -e "${RED}❌ Connection failed. Is PX4 running?${NC}"
        fi
        ;;

    build)
        echo -e "${YELLOW}🔨 Rebuilding images...${NC}"
        docker compose build --no-cache
        echo -e "${GREEN}✅ Build complete!${NC}"
        ;;

    clean)
        echo -e "${RED}🧹 Cleaning up...${NC}"
        docker compose down -v --rmi all
        echo -e "${GREEN}✅ Clean complete!${NC}"
        ;;

    *)
        echo -e "${YELLOW}Usage: $0 {start|stop|restart|status|logs|shell|test|build|clean}${NC}"
        echo ""
        echo "  start    - Start all services"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  status   - Show service status"
        echo "  logs     - View logs"
        echo "  shell    - Enter a container (px4-gazebo or ros2-bridge)"
        echo "  test     - Test the ROS 2 bridge connection"
        echo "  build    - Rebuild images"
        echo "  clean    - Remove everything"
        exit 1
esac
