"""
InDE MVP v5.1b.0 - GitHub Role Mapper

Translation tables and mapping logic for GitHub → InDE role synchronization.
Implements the two-layer RBAC mapping with human floor enforcement.
"""

from typing import Optional, Tuple

# =============================================================================
# GITHUB → INDE ROLE TRANSLATION TABLES
# =============================================================================

# Layer 1: Org Role Mapping
GITHUB_ORG_ROLE_TO_INDE = {
    "owner": "org_admin",           # GitHub org owners → InDE org admins
    "admin": "org_admin",           # GitHub admin role (alternative)
    "member": "org_member",         # Standard GitHub org members
    "outside_collaborator": "org_viewer",  # Collaborators → read-only org visibility
}

# Layer 2: Repo Role → Pursuit Role Mapping
# Note: repo admin → editor (NOT owner) - see design decision in Section 3.2
GITHUB_REPO_ROLE_TO_INDE_PURSUIT = {
    "admin": "editor",      # GitHub repo admins do NOT become pursuit owners
    "maintain": "editor",   # Maintain-level access → full editing
    "write": "editor",      # Write access → editing
    "triage": "viewer",     # Triage-only → read-only
    "read": "viewer",       # Read-only access
}

# Role hierarchy for comparison (ascending order)
ROLE_HIERARCHY = ["org_viewer", "org_member", "org_admin"]

# Pursuit role hierarchy (ascending order)
PURSUIT_ROLE_HIERARCHY = ["viewer", "editor", "owner"]


class GitHubRoleMapper:
    """
    Maps GitHub organization and repository roles to InDE roles.

    Design principles:
    - Translation, not authority: GitHub is a signal source, not the authority
    - Human floor enforcement: sync can elevate but never demote below human-set
    - Two-layer independence: org_role and pursuit_role remain independent
    """

    def map_org_role(self, github_role: str) -> str:
        """
        Map GitHub organization role to InDE organization role.

        Args:
            github_role: GitHub org role (owner, member, outside_collaborator)

        Returns:
            InDE org role. Unknown roles default to org_viewer (safe fallback).
        """
        if not github_role:
            return "org_viewer"
        return GITHUB_ORG_ROLE_TO_INDE.get(github_role.lower(), "org_viewer")

    def map_repo_role(self, github_repo_role: str) -> str:
        """
        Map GitHub repository role to InDE pursuit role.

        Args:
            github_repo_role: GitHub repo role (admin, maintain, write, triage, read)

        Returns:
            InDE pursuit role. Unknown roles default to viewer.
        """
        if not github_repo_role:
            return "viewer"
        return GITHUB_REPO_ROLE_TO_INDE_PURSUIT.get(github_repo_role.lower(), "viewer")

    def max_role(self, role_a: Optional[str], role_b: Optional[str]) -> str:
        """
        Return the higher of two org roles per the defined hierarchy.

        Args:
            role_a: First role to compare
            role_b: Second role to compare

        Returns:
            The higher-ranked role
        """
        if not role_a and not role_b:
            return "org_viewer"
        if not role_a:
            return role_b
        if not role_b:
            return role_a

        try:
            idx_a = ROLE_HIERARCHY.index(role_a)
        except ValueError:
            idx_a = 0  # Unknown role → lowest

        try:
            idx_b = ROLE_HIERARCHY.index(role_b)
        except ValueError:
            idx_b = 0  # Unknown role → lowest

        return ROLE_HIERARCHY[max(idx_a, idx_b)]

    def max_pursuit_role(self, role_a: Optional[str], role_b: Optional[str]) -> str:
        """
        Return the higher of two pursuit roles per the defined hierarchy.

        Args:
            role_a: First role to compare
            role_b: Second role to compare

        Returns:
            The higher-ranked pursuit role
        """
        if not role_a and not role_b:
            return "viewer"
        if not role_a:
            return role_b
        if not role_b:
            return role_a

        try:
            idx_a = PURSUIT_ROLE_HIERARCHY.index(role_a)
        except ValueError:
            idx_a = 0

        try:
            idx_b = PURSUIT_ROLE_HIERARCHY.index(role_b)
        except ValueError:
            idx_b = 0

        return PURSUIT_ROLE_HIERARCHY[max(idx_a, idx_b)]

    def compute_effective_role(
        self,
        github_derived_role: Optional[str],
        human_set_role: Optional[str],
        current_role: str
    ) -> Tuple[str, bool]:
        """
        Compute effective role with human floor enforcement.

        The human floor rule ensures that GitHub sync can elevate or match
        a role, but never demote below what a human admin has explicitly set.

        Args:
            github_derived_role: Role derived from GitHub (None if not in GitHub org)
            human_set_role: Role explicitly set by human admin (the floor)
            current_role: Current effective role

        Returns:
            Tuple of (effective_role, human_floor_was_applied)
            - effective_role: The computed role to use
            - human_floor_was_applied: True if human floor prevented a lower role
        """
        # If user not found in GitHub, keep current role
        if github_derived_role is None:
            return (current_role, False)

        # If no human-set role, use GitHub-derived role
        if human_set_role is None:
            return (github_derived_role, False)

        # Compute max(github_derived_role, human_set_role)
        effective = self.max_role(github_derived_role, human_set_role)

        # Check if human floor prevented demotion
        human_floor_applied = (effective == human_set_role and
                               effective != github_derived_role)

        return (effective, human_floor_applied)

    def compute_effective_pursuit_role(
        self,
        github_derived_pursuit_role: Optional[str],
        human_set_pursuit_role: Optional[str],
        current_pursuit_role: Optional[str]
    ) -> Tuple[str, bool]:
        """
        Compute effective pursuit role with human floor enforcement (Layer 2).

        The human floor rule ensures that GitHub sync can elevate or match
        a pursuit role, but never demote below what a human admin has set.

        Two-layer independence: This method only deals with pursuit roles,
        never touches or considers org roles.

        Args:
            github_derived_pursuit_role: Role derived from GitHub repo permissions
            human_set_pursuit_role: Role explicitly set by human admin (the floor)
            current_pursuit_role: Current pursuit role (may be None if new)

        Returns:
            Tuple of (effective_pursuit_role, human_floor_was_applied)
        """
        # If user not in GitHub repo, keep current role or default to viewer
        if github_derived_pursuit_role is None:
            return (current_pursuit_role or "viewer", False)

        # If no human-set role, use GitHub-derived role
        if human_set_pursuit_role is None:
            return (github_derived_pursuit_role, False)

        # Compute max(github_derived_pursuit_role, human_set_pursuit_role)
        effective = self.max_pursuit_role(github_derived_pursuit_role, human_set_pursuit_role)

        # Check if human floor prevented demotion
        human_floor_applied = (effective == human_set_pursuit_role and
                               effective != github_derived_pursuit_role)

        return (effective, human_floor_applied)

    def pursuit_role_index(self, role: str) -> int:
        """Get the numeric index of a pursuit role in the hierarchy."""
        try:
            return PURSUIT_ROLE_HIERARCHY.index(role)
        except ValueError:
            return 0

    def role_index(self, role: str) -> int:
        """Get the numeric index of a role in the hierarchy."""
        try:
            return ROLE_HIERARCHY.index(role)
        except ValueError:
            return 0

    def is_valid_org_role(self, role: str) -> bool:
        """Check if a role is a valid InDE org role."""
        return role in ROLE_HIERARCHY

    def is_valid_pursuit_role(self, role: str) -> bool:
        """Check if a role is a valid InDE pursuit role."""
        return role in PURSUIT_ROLE_HIERARCHY
