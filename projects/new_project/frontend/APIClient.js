class APIClient {
    constructor(baseURL) {
        this.baseURL = baseURL || 'http://localhost:8000';
    }
    async listItems() {
        const res = await fetch(`${this.baseURL}/api/v1/items/`);
        return await res.json();
    }
    async createItem(data) {
        const res = await fetch(`${this.baseURL}/api/v1/items/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await res.json();
    }
}
export { APIClient };
export default APIClient;
