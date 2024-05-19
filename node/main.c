#include <tox/tox.h>
#include <sodium/utils.h>
#include <pthread.h>
#include <unistd.h>
#include <string.h>
#include "tox_utils.h"
#include "redis_utils.h"
#include "callbacks.h"
#include "dht_nodes.h"

#define SAVE_FILE "./tox/tox_save.tox"
#define BACKUP_FILE "./tox/tox_save_backup.tox"
#define FRIENDS_FILE "./tox/friends.tox"

Tox *tox;
redisContext *context;

void setup_dht_nodes(Tox *tox) {
    for (size_t i = 0; i < sizeof(dht_nodes) / sizeof(DHT_node); i++) {
        unsigned char key_bin[TOX_PUBLIC_KEY_SIZE];
        sodium_hex2bin(key_bin, sizeof(key_bin), dht_nodes[i].key_hex, sizeof(dht_nodes[i].key_hex) - 1, NULL, NULL, NULL);
        tox_bootstrap(tox, dht_nodes[i].ip, dht_nodes[i].port, key_bin, NULL);
    }
}

int main() {
    tox = load_tox(SAVE_FILE);
    context = connect_redis();

    if (!tox || !context) {
        printf("Initialization failed\n");
        return 1;
    }

    pthread_t subscriber_thread;
    if (pthread_create(&subscriber_thread, NULL, redis_subscriber, context) != 0) {
        printf("Failed to create Redis subscriber thread\n");
        return 1;
    }

    const char *name = "Wormhole Tox Node";
    tox_self_set_name(tox, (const uint8_t*) name, strlen(name), NULL);

    const char *status_message = "Based";
    tox_self_set_status_message(tox, (const uint8_t*) status_message, strlen(status_message), NULL);

    setup_dht_nodes(tox);

    char tox_id_hex[TOX_ADDRESS_SIZE * 2 + 1];
    get_tox_id(tox, tox_id_hex);
    printf("Tox ID: %s\n", tox_id_hex);

    register_callbacks(tox);
    load_friends(tox, FRIENDS_FILE);

    printf("Connecting...\n");

    while (1) {
        tox_iterate(tox, NULL);
        usleep(tox_iteration_interval(tox) * 1000);

        save_tox(tox, SAVE_FILE);
        save_tox(tox, BACKUP_FILE);
    }

    tox_kill(tox);
    redisFree(context);

    return 0;
}
