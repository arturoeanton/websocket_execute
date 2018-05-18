# websocket_execute

# This solution need that dockers are running
docker run -d --hostname my-rabbit --name my-rabbit -p 4369:4369 -p 5671:5671 -p 25672:25672 -p 5672:5672 rabbitmq
docker run -d --hostname my-redis --name my-redis -p 6379:6379 redis
