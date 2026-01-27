"""Row-level access control for documents"""
from typing import List, Optional

class AccessControl:
    """Filter documents based on user's group membership"""
    
    @staticmethod
    def build_filter(user_groups: List[str]) -> Optional[dict]:
        """Build Weaviate filter for user's accessible documents
        
        Documents have 'allowed_groups' field. User can access if:
        - Document has no restrictions (allowed_groups is empty/null)
        - User's groups overlap with document's allowed_groups
        - User is admin (handled at query level)
        """
        if not user_groups:
            # No groups = only public docs
            return {
                "operator": "IsNull",
                "path": ["allowed_groups"],
                "valueBoolean": True
            }
        
        # User can see docs where their groups match OR doc is public
        return {
            "operator": "Or",
            "operands": [
                {
                    "operator": "IsNull", 
                    "path": ["allowed_groups"],
                    "valueBoolean": True
                },
                {
                    "operator": "ContainsAny",
                    "path": ["allowed_groups"],
                    "valueTextArray": user_groups
                }
            ]
        }
    
    @staticmethod
    def can_access(user_groups: List[str], doc_groups: List[str]) -> bool:
        """Check if user can access a specific document"""
        if not doc_groups:  # Public document
            return True
        if "admin" in user_groups:
            return True
        return bool(set(user_groups) & set(doc_groups))
