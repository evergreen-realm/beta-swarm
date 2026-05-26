import requests
import json
import os

SKILL_CATALOG = [
    {"name": "web-scraper", "repo": "sickn33/antigravity-awesome-skills", "category": "data", "description": "Advanced web scraping patterns"},
    {"name": "api-tester", "repo": "sickn33/antigravity-awesome-skills", "category": "testing", "description": "Automated API testing suite"},
    {"name": "docs-generator", "repo": "sickn33/antigravity-awesome-skills", "category": "docs", "description": "Auto-generates documentation from code"},
    {"name": "security-scanner", "repo": "sickn33/antigravity-awesome-skills", "category": "security", "description": "Scans for common vulnerabilities"},
    {"name": "performance-profiler", "repo": "sickn33/antigravity-awesome-skills", "category": "performance", "description": "Profiles code performance bottlenecks"},
]

class SkillsMarketplace:
    def __init__(self):
        self.cache_file = "beta_swarm/dashboard/skills_cache.json"
        self.local_skills_dir = "skills"
        os.makedirs(self.local_skills_dir, exist_ok=True)

    def search(self, query: str = ""):
        # Try GitHub API first
        try:
            resp = requests.get(
                f"https://api.github.com/search/repositories?q=antigravity+skills+{query}",
                timeout=5,
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            if resp.status_code == 200:
                items = resp.json().get("items", [])[:10]
                results = [{"name": i["name"], "repo": i["full_name"], "stars": i["stargazers_count"], "source": "github"} for i in items]
                self._update_cache(results)
                return results
        except Exception as e:
            print(f"GitHub API failed: {e}")

        # Fallback 1: Local catalog
        results = [s for s in SKILL_CATALOG if query.lower() in s["name"].lower()]
        if results:
            self._update_cache(results)
            return [{**s, "source": "catalog"} for s in results]

        # Fallback 2: Cached results
        if os.path.exists(self.cache_file):
            with open(self.cache_file) as f:
                cached = json.load(f)
            return [c for c in cached if query.lower() in c.get("name", "").lower()]

        # Fallback 3: Empty with message
        return [{"name": "No results", "repo": "", "source": "fallback", "message": "GitHub unavailable. Try again later."}]

    def install(self, repo: str):
        # Clone to skills/{repo_name}/
        import subprocess
        name = repo.split("/")[-1]
        target = os.path.join(self.local_skills_dir, name)
        try:
            subprocess.run(["git", "clone", f"https://github.com/{repo}.git", target], check=True, timeout=30)
            # Register in KuzuDB
            try:
                from beta_swarm.brain.kuzu_manager import KuzuBrain
                brain = KuzuBrain()
                brain.query(f"CREATE (s:Skill {{name: '{name}', repo: '{repo}', path: '{target}', status: 'installed'}})")
            except:
                pass # Graceful fallback if no DB
            return {"status": "installed", "path": target}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _update_cache(self, results):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump(results, f, indent=2)
