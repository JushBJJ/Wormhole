#include "tox_utils.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sodium/utils.h>

Tox* load_tox(const char *filename) {
    FILE *file = fopen(filename, "rb");
    if (!file) return tox_new(NULL, NULL);

    struct stat st;
    if (stat(filename, &st) != 0 || st.st_size == 0) {
        fclose(file);
        remove(filename);
        return tox_new(NULL, NULL);
    }

    fseek(file, 0, SEEK_END);
    size_t size = ftell(file);
    fseek(file, 0, SEEK_SET);
    uint8_t *data = calloc(size, sizeof(uint8_t));
    if (!data) {
        fclose(file);
        return tox_new(NULL, NULL);
    }

    fread(data, sizeof(uint8_t), size, file);
    fclose(file);

    struct Tox_Options options;
    tox_options_default(&options);
    options.savedata_type = TOX_SAVEDATA_TYPE_TOX_SAVE;
    options.savedata_data = data;
    options.savedata_length = size;

    Tox *tox = tox_new(&options, NULL);
    free(data);

    if (!tox) {
        remove(filename);
        return tox_new(NULL, NULL);
    }

    return tox;
}

void save_tox(Tox *tox, const char *filename) {
    FILE *file = fopen(filename, "wb");
    if (!file) return;

    size_t size = tox_get_savedata_size(tox);
    uint8_t *data = calloc(size, sizeof(uint8_t));
    if (!data) {
        fclose(file);
        return;
    }

    tox_get_savedata(tox, data);
    fwrite(data, sizeof(uint8_t), size, file);
    free(data);
    fclose(file);
}

void save_friends(Tox *tox, const char *filename) {
    FILE *file = fopen(filename, "w");
    if (!file) {
        printf("Failed to save friends\n");
        return;
    }

    uint32_t friend_count = tox_self_get_friend_list_size(tox);
    uint32_t *friends = calloc(friend_count, sizeof(uint32_t));
    if (!friends) {
        fclose(file);
        return;
    }

    tox_self_get_friend_list(tox, friends);
    for (uint32_t i = 0; i < friend_count; i++) {
        char address[TOX_ADDRESS_SIZE * 2 + 1];
        tox_friend_get_public_key(tox, friends[i], (uint8_t *)address, NULL);
        fprintf(file, "%s\n", address);
    }

    free(friends);
    fclose(file);
}

void load_friends(Tox *tox, const char *filename) {
    FILE *file = fopen(filename, "r");
    if (!file) {
        printf("No friends file found\n");
        return;
    }

    char line[TOX_ADDRESS_SIZE * 2 + 1];
    while (fgets(line, sizeof(line), file)) {
        uint8_t public_key[TOX_PUBLIC_KEY_SIZE];
        sodium_hex2bin(public_key, sizeof(public_key), line, strlen(line), NULL, NULL, NULL);
        tox_friend_add_norequest(tox, public_key, NULL);
    }
    fclose(file);
}

void get_tox_id(Tox *tox, char *tox_id_hex) {
    uint8_t tox_id_bin[TOX_ADDRESS_SIZE];
    tox_self_get_address(tox, tox_id_bin);
    sodium_bin2hex(tox_id_hex, TOX_ADDRESS_SIZE * 2 + 1, tox_id_bin, TOX_ADDRESS_SIZE);
}

