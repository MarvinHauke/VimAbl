<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { ASTWebSocketClient } from '$lib/api/websocket';
	import { connectionStore } from '$lib/stores/connection';
	import { astStore } from '$lib/stores/ast';
	import ConnectionStatus from '$lib/components/ConnectionStatus.svelte';
	import TreeView from '$lib/components/TreeView.svelte';
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
					astStore.setAST(fullMessage.payload.ast, fullMessage.payload.project_path);
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

		<main class="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
			{#if !$astStore.projectPath && $astStore.root}
				<div class="bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400 p-4 m-6 mb-0">
					<div class="flex">
						<div class="flex-shrink-0">
							<svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
								<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
							</svg>
						</div>
						<div class="ml-3">
							<p class="text-sm text-yellow-700 dark:text-yellow-200">
								<strong>Unsaved Project</strong> - This project hasn't been saved yet. Save it in Ableton Live (Cmd+S) to enable full functionality.
							</p>
						</div>
					</div>
				</div>
			{/if}

			<TreeView root={$astStore.root} projectPath={$astStore.projectPath} />
		</main>
	</div>
</div>
