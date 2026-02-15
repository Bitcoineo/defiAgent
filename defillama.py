"""DeFiLlama API client with protocol resolution and caching."""

import difflib
from collections import Counter

import requests

BASE_URL = "https://api.llama.fi"
REQUEST_TIMEOUT = 30
AGGREGATE_TVL_KEYS = {"borrowed", "staking", "pool2", "vesting", "offers"}


class DefiLlamaAPIError(Exception):
    """Raised when an API request fails."""
    pass


class ProtocolNotFoundError(Exception):
    """Raised when the user-provided protocol name cannot be resolved."""
    pass


class DefiLlamaClient:
    """HTTP client for the DeFiLlama API with caching and protocol resolution."""

    def __init__(self, timeout=REQUEST_TIMEOUT):
        self.session = requests.Session()
        self.timeout = timeout
        self._protocols_cache = None
        self._hacks_cache = None

    def _get(self, path):
        """Make a GET request and return parsed JSON."""
        url = f"{BASE_URL}{path}"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.ConnectionError as e:
            raise DefiLlamaAPIError(f"Connection failed for {url}: {e}")
        except requests.Timeout:
            raise DefiLlamaAPIError(f"Request timed out for {url}")
        except requests.HTTPError as e:
            raise DefiLlamaAPIError(f"HTTP {resp.status_code} for {url}: {e}")
        except ValueError:
            raise DefiLlamaAPIError(f"Invalid JSON response from {url}")

    def get_protocols_list(self):
        """Fetch and cache the full protocols list."""
        if self._protocols_cache is None:
            self._protocols_cache = self._get("/protocols")
        return self._protocols_cache

    def get_protocol_detail(self, slug):
        """Fetch full protocol detail by slug."""
        return self._get(f"/protocol/{slug}")

    def get_all_hacks(self):
        """Fetch and cache all hack records."""
        if self._hacks_cache is None:
            self._hacks_cache = self._get("/hacks")
        return self._hacks_cache

    def resolve_protocol(self, user_input):
        """Resolve user input to a protocol slug and metadata.

        Returns dict with keys: slug, name, is_parent, children, category
        """
        protocols = self.get_protocols_list()
        normalized = user_input.strip().lower()

        # Build lookup structures
        slug_map = {}
        name_map = {}
        parent_slugs = set()
        parent_children = {}  # parent_slug -> list of child protocols

        for p in protocols:
            slug = p.get("slug", "")
            name = p.get("name", "")
            slug_map[slug.lower()] = p
            name_map[name.lower()] = p

            parent_ref = p.get("parentProtocol", "")
            if parent_ref and parent_ref.startswith("parent#"):
                ps = parent_ref.split("#", 1)[1]
                parent_slugs.add(ps.lower())
                parent_children.setdefault(ps.lower(), []).append(p)

        # Step 1: Exact slug match
        if normalized in slug_map:
            p = slug_map[normalized]
            return {
                "slug": p["slug"],
                "name": p["name"],
                "is_parent": False,
                "children": [],
                "category": p.get("category"),
            }

        # Step 2: Exact name match
        if normalized in name_map:
            p = name_map[normalized]
            return {
                "slug": p["slug"],
                "name": p["name"],
                "is_parent": False,
                "children": [],
                "category": p.get("category"),
            }

        # Step 3: Parent protocol match (by slug, slug-as-words, or derived display name)
        if normalized in parent_slugs:
            return self._build_parent_result(normalized, parent_children)

        for ps in parent_slugs:
            if normalized == ps.replace("-", " "):
                return self._build_parent_result(ps, parent_children)

        # Also match against parent display names derived from children
        parent_name_map = {}  # display_name.lower() -> parent_slug
        for ps, children in parent_children.items():
            for child in children:
                child_name = child.get("name", "")
                base = child_name.split(" V")[0].split(" v")[0].strip()
                parent_name_map[base.lower()] = ps
        if normalized in parent_name_map:
            return self._build_parent_result(parent_name_map[normalized], parent_children)

        # Step 4: Fuzzy matching
        all_candidates = {}
        for slug in slug_map:
            all_candidates[slug] = ("slug", slug)
        for name in name_map:
            all_candidates[name] = ("name", name)
        for ps in parent_slugs:
            all_candidates[ps] = ("parent", ps)
        for pname, ps in parent_name_map.items():
            all_candidates[pname] = ("parent", ps)

        matches = difflib.get_close_matches(
            normalized, all_candidates.keys(), n=5, cutoff=0.85
        )

        if matches:
            best = matches[0]
            kind, key = all_candidates[best]

            if kind == "parent":
                return self._build_parent_result(key, parent_children)
            elif kind == "slug":
                p = slug_map[key]
                return {
                    "slug": p["slug"],
                    "name": p["name"],
                    "is_parent": False,
                    "children": [],
                    "category": p.get("category"),
                }
            else:
                p = name_map[key]
                return {
                    "slug": p["slug"],
                    "name": p["name"],
                    "is_parent": False,
                    "children": [],
                    "category": p.get("category"),
                }

        # No match found — gather suggestions
        all_names = [p.get("name", "") for p in protocols]
        suggestions = difflib.get_close_matches(normalized, [n.lower() for n in all_names], n=3, cutoff=0.4)
        suggestion_names = []
        for s in suggestions:
            for p in protocols:
                if p.get("name", "").lower() == s:
                    suggestion_names.append(p["name"])
                    break

        msg = f"Protocol '{user_input}' not found."
        if suggestion_names:
            msg += f" Did you mean: {', '.join(suggestion_names)}?"
        raise ProtocolNotFoundError(msg)

    def _build_parent_result(self, parent_slug, parent_children):
        """Build resolution result for a parent protocol."""
        children = parent_children.get(parent_slug, [])

        # Derive category from children
        categories = [c.get("category") for c in children if c.get("category")]
        category = Counter(categories).most_common(1)[0][0] if categories else None

        # Derive display name from parent slug or first child
        name = parent_slug.replace("-", " ").title()
        for child in children:
            # Use the child name without version suffix if it matches
            child_name = child.get("name", "")
            base = child_name.split(" V")[0].split(" v")[0].strip()
            if base.lower() == parent_slug.replace("-", " "):
                name = base
                break

        return {
            "slug": parent_slug,
            "name": name,
            "is_parent": True,
            "children": [{"name": c["name"], "slug": c["slug"]} for c in children],
            "category": category,
        }

    def find_hacks_for_protocol(self, protocol_name, child_names=None):
        """Filter hack records matching this protocol or its children."""
        hacks = self.get_all_hacks()
        names_to_match = {protocol_name.lower()}
        if child_names:
            names_to_match.update(n.lower() for n in child_names)

        return [h for h in hacks if h.get("name", "").lower() in names_to_match]
