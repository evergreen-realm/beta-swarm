// Monaco Editor Lazy Loader
require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.36.1/min/vs' } });
require(['vs/editor/editor.main'], function () {
    window.monacoEditorInstance = monaco.editor.create(document.getElementById('editor-container'), {
        value: '// Beta Swarm S5 LevelCode Area\n// Generating logic...\n',
        language: 'python',
        theme: 'vs-dark',
        automaticLayout: true,
        minimap: { enabled: false },
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        fontSize: 14
    });

    // Optional Build WebSocket
    const buildWs = new WebSocket(`ws://${window.location.host}/ws/build`);
    buildWs.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === "code_update") {
            window.monacoEditorInstance.setValue(msg.code);
        }
    };
});
