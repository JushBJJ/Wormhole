#ifndef CALLBACKS_H
#define CALLBACKS_H

#include <tox/tox.h>

void register_callbacks(Tox *tox);
void friend_request_cb(Tox *tox, const uint8_t *public_key, const uint8_t *message, size_t length, void *user_data);
void friend_message_cb(Tox *tox, uint32_t friend_number, TOX_MESSAGE_TYPE type, const uint8_t *message, size_t length, void *user_data);
void self_connection_status_cb(Tox *tox, TOX_CONNECTION connection_status, void *user_data);

#endif // CALLBACKS_H
