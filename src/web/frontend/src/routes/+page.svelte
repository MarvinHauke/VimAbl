<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { ASTWebSocketClient } from '$lib/api/websocket';
	import { connectionStore } from '$lib/stores/connection';
	import { astStore } from '$lib/stores/ast';
	import ConnectionStatus from '$lib/components/ConnectionStatus.svelte';
	import type { WebSocketMessage, FullASTMessage } from '$lib/types/ast';

	let client: ASTWebSocketClient | null = null;

	onMount(() => {
		const wsUrl = `ws://${window.location.hostname}:8765`;
		console.log('Connecting to:', wsUrl);

		client = new ASTWebSocketClient({
			url: wsUrl,
			onStatusChange: (status) => connectionStore.setStatus(status),
			onMessage: (message: WebSocketMessage) => {
				connectionStore.updateLastUpdate();
				if (message.type === 'FULL_AST') {
					const fullMessage = message as FullASTMessage;
					astStore.setAST(fullMessage.payload.ast);
				} else if (message.type === 'ERROR') {
					connectionStore.setError(message.payload.error);
				}
			},
			onError: (error) => connectionStore.setError(error.message)
		});

		client.connect();
	});

	onDestroy(() => {
		if (client) client.disconnect();
	});
</script>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
	<div class="max-w-7xl mx-auto">
		<header class="mb-8">
			<h1 class="text-4xl font-bold text-gray-900 dark:text-white mb-4">🎧 VimAbl AST TreeViewer</h1>
			<p class="text-gray-600 dark:text-gray-400 mb-4">Real-time Ableton Live project visualization</p>
			<ConnectionStatus />
		</header>

		<main class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
			{#if $astStore.root}
				<div class="space-y-4">
					<h2 class="text-2xl font-semibold text-gray-900 dark:text-white">Project AST</h2>
					<div class="bg-gray-50 dark:bg-gray-900 rounded p-4 font-mono text-sm">
						<div><strong>Type:</strong> {$astStore.root.node_type}</div>
						<div><strong>ID:</strong> {$astStore.root.id}</div>
						<div><strong>Children:</strong> {$astStore.root.children?.length || 0}</div>
					</div>

					{#if $astStore.root.children && $astStore.root.children.length > 0}
						<h3 class="text-lg font-semibold text-gray-900 dark:text-white">First 10 Nodes:</h3>
						{#each $astStore.root.children.slice(0, 10) as child}
							<div class="bg-blue-50 dark:bg-blue-900/20 rounded p-3 text-sm">
								<div><strong>Type:</strong> {child.node_type}</div>
								<div><strong>ID:</strong> {child.id}</div>
								{#if child.attributes?.name}
									<div><strong>Name:</strong> {child.attributes.name || '(unnamed)'}</div>
								{/if}
							</div>
						{/each}
					{/if}
				</div>
			{:else}
				<div class="text-center py-12 text-gray-500 dark:text-gray-400">
					<p class="text-lg">Waiting for AST data...</p>
					<p class="text-sm mt-2">Ensure WebSocket server is running on port 8765</p>
				</div>
			{/if}
		</main>
	</div>
</div>
