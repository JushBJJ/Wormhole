#ifndef REDIS_UTILS_H
#define REDIS_UTILS_H

#include <hiredis/hiredis.h>

#define REDIS_SUBSCRIBE_CHANNEL "tox_node"
#define DISCORD_CHANNEL "wormhole_channel"
#define PREPEND_MESSAGE "{\"message\": \"[Tox Node]:\"}"

redisContext* connect_redis();
void publish_to_channel(redisContext *context, const char *channel, const char *message);
void publish_to_channel_raw(redisContext *context, const char *channel, const char *message);
void* redis_subscriber(void *arg);

#endif // REDIS_UTILS_H
