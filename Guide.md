# Discord

After inviting your wormhole discord bot into your server, make sure it has the appropriate send and read permissions in the appropriate channels.

## Connect your channels 
By default, the following channel categories are enabled:
1. general
2. wormhole
3. happenings
4. qotd
5. memes
6. computers
7. finance
8. music
9. cats

So for example in your general channel you can type:
```
%join general
```

It is **highly reccomended** that you create a dedicated wormhole channel.

```
%join wormhole
```

## Leaving channels
```
%leave
```

Note: If you accidentally joined two channels, you may have to say `%leave` more than once.

## Connect Server
This command lets you manually re/connect the server without adding any **additional** channels. If you've disconnected your server before, the channels that are already saved in `config.json` won't be deleted unless you manually remove them.
```
%connect
```

## Disconnect Server
This disconnects the whole server from being connected to wormhole, however this will not remove the channels that were already listed in your `config.json` file.
```
%disonnect
```

# Tox Node
## Getting your Wormhole's Tox ID
When you start your wormhole node, your tox ID will be automatically be printed out to the terminal.

Alternatively, you can do the following command in discord:
```
%tox-id
```
Note: This will only send back the tox id in the `wormhole` channels that are connected. Not at the same channel that you did the command in - i know...un-intuitive.

## Connecting to another tox node
First, get the other tox node's Tox ID, this could be either from asking the node owner or getting it by using the `tox-id` command in their discord server.

After that, go back to your own wormhole discord bot and run the command:
```
%tox-add <INSERT TOX ID HERE>
```

## Removing the tox node from your friend list
To be added.