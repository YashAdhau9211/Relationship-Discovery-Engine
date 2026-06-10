from app.schemas.social import MutualConnectionResponse, SocialConnectionsResponse, SocialProfileResponse


class SocialService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def get_social_profile(self, entity_id: str, limit: int = 10) -> SocialProfileResponse:
        followers = self.repository.get_followers(entity_id, limit=limit)
        following = self.repository.get_following(entity_id, limit=limit)
        friends = self.repository.get_friends(entity_id, limit=limit)
        counts = self.repository.social_counts(entity_id)

        follower_count = counts["follower_count"]
        following_count = counts["following_count"]
        follow_ratio = round(follower_count / following_count, 4) if following_count else None

        return SocialProfileResponse(
            entity_id=entity_id,
            follower_count=follower_count,
            following_count=following_count,
            friend_count=counts["friend_count"],
            mutual_count=counts["mutual_count"],
            follow_ratio=follow_ratio,
            platform_distribution=self.repository.platform_distribution(entity_id),
            top_followers=followers,
            top_following=following,
            friends=friends,
        )

    def get_followers(self, entity_id: str, limit: int = 50) -> SocialConnectionsResponse:
        results = self.repository.get_followers(entity_id, limit=limit)
        return SocialConnectionsResponse(
            entity_id=entity_id,
            relationship_type="FOLLOWS",
            direction="incoming",
            count=len(results),
            results=results,
        )

    def get_following(self, entity_id: str, limit: int = 50) -> SocialConnectionsResponse:
        results = self.repository.get_following(entity_id, limit=limit)
        return SocialConnectionsResponse(
            entity_id=entity_id,
            relationship_type="FOLLOWS",
            direction="outgoing",
            count=len(results),
            results=results,
        )

    def get_friends(self, entity_id: str, limit: int = 50) -> SocialConnectionsResponse:
        results = self.repository.get_friends(entity_id, limit=limit)
        return SocialConnectionsResponse(
            entity_id=entity_id,
            relationship_type="FRIENDS_WITH",
            direction="undirected",
            count=len(results),
            results=results,
        )

    def get_mutuals(self, source_id: str, target_id: str, limit: int = 50) -> MutualConnectionResponse:
        mutuals = self.repository.get_shared_neighbors(source_id=source_id, target_id=target_id, limit=limit)
        return MutualConnectionResponse(
            source_id=source_id,
            target_id=target_id,
            count=len(mutuals),
            mutuals=mutuals,
        )
