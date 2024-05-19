#include "redis_utils.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <tox/tox.h>
#include <sodium/utils.h>
#include "tox_utils.h"

extern Tox *tox;

redisContext* connect_redis() {
    redisContext *context = redisConnect("127.0.0.1", 6379);
    if (context == NULL || context->err) {
        if (context) {
            printf("Error: %s\n", context->errstr);
            redisFree(context);
        } else {
            printf("Can't allocate redis context\n");
        }
        return NULL;
    }
    return context;
}

void publish_to_channel(redisContext *context, const char *channel, const char *message) {
    int prepend_length = strlen(PREPEND_MESSAGE);
    char *formatted_message = calloc(strlen(message) + prepend_length + 1, sizeof(char));
    if (formatted_message == NULL) {
        printf("Memory allocation failed in publish_to_channel\n");
        return;
    }
    sprintf(formatted_message, "{\"message\": \"[Tox Node]: %s\"}", message);
    redisReply *reply = redisCommand(context, "PUBLISH %s %s", channel, formatted_message);

    if (reply != NULL) {
        printf("Published message to channel: %s\n", message);
    } else {
        printf("Failed to publish message to channel\n");
    }
    freeReplyObject(reply);
    free(formatted_message);
}

void publish_to_channel_raw(redisContext *context, const char *channel, const char *message) {
    redisReply *reply = redisCommand(context, "PUBLISH %s %s", channel, message);

    if (reply != NULL) {
        printf("Published message to channel: %s\n", message);
    } else {
        printf("Failed to publish message to channel\n");
    }
    freeReplyObject(reply);
}

void* redis_subscriber(void *arg) {
    redisContext *context = (redisContext *)arg;
    redisContext *subscriber_context = redisConnect("127.0.0.1", 6379);
    if (subscriber_context == NULL || subscriber_context->err) {
        if (subscriber_context) {
            printf("Error: %s\n", subscriber_context->errstr);
            redisFree(subscriber_context);
        } else {
            printf("Can't allocate redis context for subscriber\n");
        }
        return NULL;
    }

    redisReply *reply = redisCommand(subscriber_context, "SUBSCRIBE %s", REDIS_SUBSCRIBE_CHANNEL);
    if (reply == NULL) {
        printf("Failed to subscribe to channel\n");
        redisFree(subscriber_context);
        return NULL;
    }
    freeReplyObject(reply);

    printf("Subscribed to channel %s\n", REDIS_SUBSCRIBE_CHANNEL);

    while (redisGetReply(subscriber_context, (void **)&reply) == REDIS_OK) {
        if (reply->type == REDIS_REPLY_ARRAY && reply->elements == 3) {
            if (strcmp(reply->element[0]->str, "message") == 0) {
                const char *channel = reply->element[1]->str;
                const char *message = reply->element[2]->str;
                printf("%s\n", message);

                if (strncmp(message, "COMMAND: ", 9) == 0) {
                    const char *command = message + 9;
                    if (strncmp(command, "ADD", 3) == 0) {
                        // Add node
                        const char *tox_id = command + 4;
                        char *prepend = "ADD";
                        char *message = calloc(strlen(prepend) + strlen(tox_id) + 1, sizeof(char));
                        if (message == NULL) {
                            printf("Memory allocation failed in redis_subscriber\n");
                            continue;
                        }
                        char *msg = "Feel the AGI.";
                        uint8_t tox_address[TOX_ADDRESS_SIZE];
                        TOX_ERR_FRIEND_ADD err;

                        if (sodium_hex2bin(tox_address, sizeof(tox_address),
                                           tox_id, strlen(tox_id),
                                           NULL, NULL, NULL) != 0) {
                            printf("Failed to convert tox_id to binary\n");
                            free(message);
                            continue;
                        }

                        tox_friend_add(tox, tox_address, (const uint8_t *)msg, strlen(msg), &err);

                        if (err != TOX_ERR_FRIEND_ADD_OK) {
                            printf("Failed to send friend request\n");
                            char *err_message = calloc(100, sizeof(char));
                            if (err_message == NULL) {
                                printf("Memory allocation failed for error message\n");
                                free(message);
                                continue;
                            }

                            switch (err) {
                                case TOX_ERR_FRIEND_ADD_NULL:
                                    sprintf(err_message, "The friend address was NULL.\n");
                                    break;
                                case TOX_ERR_FRIEND_ADD_TOO_LONG:
                                    sprintf(err_message, "The friend address was too long.\n");
                                    break;
                                case TOX_ERR_FRIEND_ADD_NO_MESSAGE:
                                    sprintf(err_message, "The message was NULL, but the message length was greater than 0.\n");
                                    break;
                                case TOX_ERR_FRIEND_ADD_OWN_KEY:
                                    sprintf(err_message, "The friend address was the same as the user's own address.\n");
                                    break;
                                case TOX_ERR_FRIEND_ADD_ALREADY_SENT:
                                    sprintf(err_message, "The friend request was already sent.\n");
                                    break;
                                case TOX_ERR_FRIEND_ADD_BAD_CHECKSUM:
                                    sprintf(err_message, "The friend address checksum was invalid.\n");
                                    break;
                                case TOX_ERR_FRIEND_ADD_SET_NEW_NOSPAM:
                                    sprintf(err_message, "The friend address was invalid, but a new nospam was set.\n");
                                    break;
                                case TOX_ERR_FRIEND_ADD_MALLOC:
                                    sprintf(err_message, "Memory allocation failed when adding a friend.\n");
                                    break;
                                default:
                                    printf("Unknown error\n");
                                    break;
                            }

                            printf("%s\n", err_message);
                            publish_to_channel(context, DISCORD_CHANNEL, err_message);
                            free(err_message);
                            free(message);
                            save_friends(tox, "./tox/friends.tox");
                            continue;
                        }

                        printf("Friend request sent\n");
                        sprintf(message, "%s %s", prepend, tox_id);
                        printf("%s\n", message);
                        publish_to_channel(context, DISCORD_CHANNEL, message);
                        free(message);

                    } else if (strncmp(command, "LIST", 4) == 0) {
                        // Get connected nodes
                        uint32_t friend_count = tox_self_get_friend_list_size(tox);
                        uint32_t *friends = calloc(friend_count, sizeof(uint32_t));
                        if (friends) {
                            tox_self_get_friend_list(tox, friends);

                            char *msg = "LIST ";
                            char *friend_count_str = calloc(strlen(msg) + 1, sizeof(char));
                            if (friend_count_str == NULL) {
                                printf("Memory allocation failed for friend count string\n");
                                free(friends);
                                continue;
                            }
                            char str[10];

                            sprintf(str, "%u", friend_count);
                            sprintf(friend_count_str, "%s%s", msg, str);

                            publish_to_channel(context, DISCORD_CHANNEL, friend_count_str);
                            free(friends);
                            free(friend_count_str);
                        }
                    }
                    else if (strncmp(command, "ID", 2)==0){
                        // Get Tox ID
                        uint8_t tox_id[TOX_ADDRESS_SIZE];
                        char tox_id_str[TOX_ADDRESS_SIZE * 2 + 1];
                        tox_self_get_address(tox, tox_id);

                        for(int i=0; i<TOX_ADDRESS_SIZE; i++){
                            char byte[3];
                            sprintf(byte, "%02X", tox_id[i]);
                            strcat(tox_id_str, byte);
                        }

                        printf("Tox ID: %s", tox_id_str);

                        publish_to_channel(context, DISCORD_CHANNEL, tox_id_str);
                    }
                } else {
                    uint32_t friend_count = tox_self_get_friend_list_size(tox);
                    uint32_t *friends = calloc(friend_count, sizeof(uint32_t));
                    if (friends) {
                        tox_self_get_friend_list(tox, friends);

                        for (uint32_t i = 0; i < friend_count; i++) {
                            tox_friend_send_message(tox, friends[i], TOX_MESSAGE_TYPE_NORMAL, (const uint8_t *)message, strlen(message), NULL);
                        }

                        free(friends);
                    }
                }
            }
        }
        freeReplyObject(reply);
    }

    redisFree(subscriber_context);
    return NULL;
}
