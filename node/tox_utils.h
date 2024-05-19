#ifndef TOX_UTILS_H
#define TOX_UTILS_H

#include <tox/tox.h>

Tox *load_tox(const char *filename);
void save_tox(Tox *tox, const char *filename);
void save_friends(Tox *tox, const char *filename);
void load_friends(Tox *tox, const char *filename);
void get_tox_id(Tox *tox, char *tox_id_hex);

#endif // TOX_UTILS_H
