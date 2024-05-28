<script>
    import { fade } from 'svelte/transition';
    import { onMount } from 'svelte';
    import { DataSet, Network } from 'vis-network/standalone';
    import { io } from 'socket.io-client';
    import { v4 as uuidv4 } from 'uuid';

    let channels = [];
    let servers = [];
    let activeChannel = "general";
    let messagesByChannel = {};
    let messages = [];

    let messages_div;

    let message = '';

    async function loadConfig() {
        const response = await fetch('/config');
        const config = await response.json();
        channels = config.channel_list;
        servers = config.servers;
        
        channels.forEach(channel => {
            messagesByChannel[channel] = [];
        });

        messages = messagesByChannel[activeChannel];
        createNetwork();
    }

    function createNetwork() {
        const container = document.getElementById('network');
        const nodes = new DataSet(
            servers.map((id, index) => ({
                id,
                label: index === 0 ? 'YOU' : `S${index + 1}`,
                color: index === 0 ? { background: 'green', border: 'green' } : { background: 'grey', border: 'grey' }
            }))
        );
        const edges = new DataSet(servers.map(id => ({ from: servers[0], to: id })));

        const data = { nodes, edges };
        const options = {
            physics: {
                enabled: true,
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {
                    gravitationalConstant: -50,
                    centralGravity: 0.01,
                    springLength: 100,
                    springConstant: 0.08,
                    damping: 0.4,
                    avoidOverlap: 1
                },
                stabilization: {
                    iterations: 200
                }
            },
            nodes: {
                shape: 'dot',
                size: 16,
                font: {
                    size: 14,
                    color: '#fff'
                },
                borderWidth: 2
            },
            edges: {
                width: 1,
                color: { inherit: true },
                smooth: {
                    type: 'continuous'
                }
            }
        };
        new Network(container, data, options);
    }


    function setActiveChannel(channel) {
        activeChannel = channel;
        messages = messagesByChannel[activeChannel];
        scrollToBottom();
    }

    async function sendMessage() {
        if (message.trim() !== '') {
            const response = await fetch('/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    "message": message,
                    "category": activeChannel
                })
            });

            if (response.ok) {
                messagesByChannel[activeChannel] = [...messagesByChannel[activeChannel], {
                    id: uuidv4(),
                    name: "Wormhole Operator",
                    text: message,
                    profilePic: "https://images-ext-1.discordapp.net/external/htCkg7phTr6Hvlf_vFRQsX9eYLFSvTHTQzFSTP9paKM/%3Fsize%3D4096/https/cdn.discordapp.com/avatars/562526615062577152/ee560da01a95c667dd2eb614f3812b41.png?format=webp&quality=lossless&width=50&height=50",
                    mediaPaths: [],
                    tenorGifs: []
                }];
                messages = [...messagesByChannel[activeChannel]];
                message = '';
                scrollToBottom();
            } else {
                console.error('Failed to send message');
            }
        }
    }

    function setupWebSocket() {
        const socket = io('http://localhost:5000');

        socket.on('connect', () => {
            console.log('WebSocket connection established');
        });

        socket.on('message', (data) => {
            console.log("New message received from Redis");
            console.log(data);
            try {
                const parsedMessage = JSON.parse(data);
                const { description, media_paths, tenor_gifs, author: { name, icon_url } } = parsedMessage.embed;
                const { category } = parsedMessage;

                if (messagesByChannel[category]) {
                    messagesByChannel[category] = [...messagesByChannel[category], {
                        id: uuidv4(),
                        name,
                        text: description,
                        profilePic: icon_url,
                        mediaPaths: media_paths || [],
                        tenorGifs: tenor_gifs || []
                    }];

                    if (category === activeChannel) {
                        messages = [...messagesByChannel[activeChannel]];
                        scrollToBottom();
                    }
                }
            } catch (error) {
                console.error('Error parsing message:', error);
            }
        });

        socket.on('disconnect', () => {
            console.log('WebSocket connection closed');
        });

        socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
        });
    }

    function scrollToBottom() {
        setTimeout(() => {
            messages_div.scrollTop = messages_div.scrollHeight;
        }, 0);
    }

    function extractMediaLinks(text) {
        const mediaRegex = /(https?:\/\/[^\s]+\.(?:png|jpg|gif|mp4)(?:\?[^\s]*)?)/gi;
        let match;
        const links = [];
        while ((match = mediaRegex.exec(text)) !== null) {
            links.push(match[0]);
        }
        return links;
    }

    onMount(() => {
        loadConfig();
        setupWebSocket();
    });
</script>

<main class="flex h-screen w-screen bg-neutral-900 text-white">
    <!-- Left Sidebar -->
    <div class="flex flex-col w-1/6 bg-neutral-800 p-4">
        {#each channels as channel}
            <div
                class="p-4 mb-2 rounded-lg cursor-pointer word-wrap {activeChannel === channel ? 'bg-neutral-700' : 'hover:bg-neutral-700'}"
                on:click={() => setActiveChannel(channel)}
                on:keydown={(e) => { if (e.key === 'Enter' || e.key === ' ') setActiveChannel(channel); }}
            >
                {channel}
            </div>
        {/each}
    </div>

    <!-- Middle Window for Messages -->
    <div class="flex flex-col w-6/12 p-4 justify-end">
        <h2 class="text-2xl mb-4 text-center">{activeChannel}</h2>
        <div bind:this={messages_div} class="flex flex-col overflow-auto h-full">
            {#each messages as message (message.id)}
                <div class="p-4 mb-2 bg-neutral-800 rounded-lg w-full flex items-center word-wrap">
                    <img src={message.profilePic} alt="{message.name}" class="w-10 h-10 rounded-full mr-4" />
                    <div>
                        <p class="font-bold">{message.name}</p>
                        <p>{message.text}</p>
                        {#each message.mediaPaths as mediaPath}
                            {#if mediaPath && mediaPath.endsWith('.mp4')}
                                <video class="mt-2 rounded-lg" controls>
                                    <source src={mediaPath} type="video/mp4" />
                                    Your browser does not support the video tag.
                                </video>
                            {:else if mediaPath && mediaPath.endsWith('.gif')}
                                <img src={mediaPath} alt="Media" class="mt-2 rounded-lg" />
                            {:else}
                                <img src={mediaPath} alt="Media" class="mt-2 rounded-lg" />
                            {/if}
                        {/each}
                        {#each message.tenorGifs as tenorGif}
                            <div class="tenor-gif-embed mt-2" data-postid={tenorGif} data-share-method="host" data-aspect-ratio="1.0" data-width="100%">
                                <a href={"https://tenor.com/view/" + tenorGif}>Tenor GIF</a>
                            </div>
                        {/each}
                    </div>
                </div>
            {/each}
        </div>
        <div class="mt-4">
            <input
                type="text"
                bind:value={message}
                placeholder="Type a message..."
                class="w-full p-4 bg-neutral-700 text-white rounded-lg"
                on:keydown={e => {
                    if (e.key === 'Enter') {
                        sendMessage();
                    }
                }}
            />
        </div>
    </div>

    <!-- Right Sidebar for Nodes -->
    <div class="flex flex-col flex-grow bg-neutral-800 p-4">
        <h2 class="text-xl mb-4">Nodes</h2>
        <div id="network" class="bg-neutral-700 rounded-lg h-1/2"></div>
    </div>
</main>

<style global lang="postcss">
    @tailwind base;
    @tailwind components;
    @tailwind utilities;
</style>
