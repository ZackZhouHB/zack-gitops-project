from typing import Dict, Optional
import os

class TenantConfig:
    """Multi-tenant configuration for team isolation"""
    
    # Team configurations
    TEAMS = {
        "cloud": {
            "kendra_index_id": os.getenv("CLOUD_KENDRA_INDEX_ID", ""),
            "kendra_data_source_id": os.getenv("CLOUD_KENDRA_DATA_SOURCE_ID", ""),
            "s3_prefix": "cloud-team/",
            "display_name": "Cloud Team"
        },
        "hr": {
            "kendra_index_id": os.getenv("HR_KENDRA_INDEX_ID", ""),
            "kendra_data_source_id": os.getenv("HR_KENDRA_DATA_SOURCE_ID", ""),
            "s3_prefix": "hr-team/",
            "display_name": "HR Team"
        },
        "solutions": {
            "kendra_index_id": os.getenv("SOLUTIONS_KENDRA_INDEX_ID", ""),
            "kendra_data_source_id": os.getenv("SOLUTIONS_KENDRA_DATA_SOURCE_ID", ""),
            "s3_prefix": "solutions-team/",
            "display_name": "Solutions Team"
        }
    }
    
    @classmethod
    def get_team_config(cls, team_id: str) -> Optional[Dict]:
        """Get configuration for specific team"""
        return cls.TEAMS.get(team_id)
    
    @classmethod
    def get_available_teams(cls) -> Dict:
        """Get list of available teams"""
        return {k: v["display_name"] for k, v in cls.TEAMS.items()}
    
    @classmethod
    def validate_team(cls, team_id: str) -> bool:
        """Validate if team exists"""
        return team_id in cls.TEAMS
