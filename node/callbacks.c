#include "callbacks.h"
#include "tox_utils.h"
#include "redis_utils.h"
#include <stdio.h>
#include <string.h>

extern redisContext *context;

void register_callbacks(Tox *tox) {
    tox_callback_friend_request(tox, friend_request_cb);
    tox_callback_friend_message(tox, friend_message_cb);
    tox_callback_self_connection_status(tox, self_connection_status_cb);
}

void friend_request_cb(Tox *tox, const uint8_t *public_key, const uint8_t *message, size_t length, void *user_data) {
    char message_str[100];
    uint32_t friend_number = tox_friend_add_norequest(tox, public_key, NULL);
    save_friends(tox, "./tox/friends.tox");

    snprintf(message_str, sizeof(message_str), "Accepted friend request from %d\n", friend_number);
    publish_to_channel(context, DISCORD_CHANNEL, message_str);
    printf("%s", message_str);
}

void friend_message_cb(Tox *tox, uint32_t friend_number, TOX_MESSAGE_TYPE type, const uint8_t *message, size_t length, void *user_data) {
    if (length > 2000) {
        printf("Message rejected, too long.\n");
        return;
    }
    printf("Message from friend %d: %.*s\n", friend_number, (int)length, message);
    publish_to_channel_raw(context, DISCORD_CHANNEL, (const char *)message);
}

void self_connection_status_cb(Tox *tox, TOX_CONNECTION connection_status, void *user_data) {
    switch (connection_status) {
        case TOX_CONNECTION_NONE:
            printf("Offline\n");
            break;
        case TOX_CONNECTION_TCP:
            printf("Online, using TCP\n");
            break;
        case TOX_CONNECTION_UDP:
            printf("Online, using UDP\n");
            break;
    }
}
