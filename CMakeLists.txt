cmake_minimum_required(VERSION 3.10)

project(Wormhole_Node)
set(CMAKE_C_STANDARD 23)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR})

file(MAKE_DIRECTORY ${CMAKE_SOURCE_DIR}/tox)

add_executable(Wormhole_Node
    node/main.c
    node/tox_utils.c
    node/redis_utils.c
    node/callbacks.c
)

target_include_directories(Wormhole_Node PRIVATE ${CMAKE_SOURCE_DIR}/node)
target_link_libraries(Wormhole_Node PRIVATE toxcore hiredis sodium pthread)
