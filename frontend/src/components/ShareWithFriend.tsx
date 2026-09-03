import { useEffect, useState } from "react";

import { createShare, getFriendsOverview } from "../api/client";
import type { FriendRecord } from "../api/types";

type ShareWithFriendProps = {
  itemId: number;
  itemLabel: string;
  itemType: "document" | "voice_preset";
};

export function ShareWithFriend({ itemId, itemLabel, itemType }: ShareWithFriendProps) {
  const [friends, setFriends] = useState<FriendRecord[]>([]);
  const [selectedFriendId, setSelectedFriendId] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSharing, setIsSharing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;

    void getFriendsOverview()
      .then((overview) => {
        if (!isCurrent) {
          return;
        }
        setFriends(overview.friends);
        setSelectedFriendId(overview.friends[0] ? String(overview.friends[0].user.id) : "");
      })
      .catch(() => {
        if (isCurrent) {
          setFriends([]);
        }
      })
      .finally(() => {
        if (isCurrent) {
          setIsLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  const handleShare = async () => {
    if (!selectedFriendId) {
      return;
    }

    setIsSharing(true);
    setStatusMessage(null);
    setErrorMessage(null);
    try {
      await createShare({
        recipient_user_id: Number(selectedFriendId),
        item_type: itemType,
        item_id: itemId,
      });
      const friend = friends.find((candidate) => String(candidate.user.id) === selectedFriendId);
      setStatusMessage(
        `Shared ${itemLabel} with ${friend?.user.display_name ?? "your friend"}. They can accept it from their Friends page.`,
      );
    } catch (shareError) {
      setErrorMessage(shareError instanceof Error ? shareError.message : "Unable to share right now");
    } finally {
      setIsSharing(false);
    }
  };

  if (isLoading) {
    return null;
  }

  if (friends.length === 0) {
    return (
      <p className="voices-page__summary-copy">
        Add a friend on the Friends page to share {itemType === "document" ? "this book" : "this narrator"}.
      </p>
    );
  }

  return (
    <div className="share-with-friend">
      <label className="library-page__field">
        <span>Share with a friend</span>
        <select
          aria-label={`Share ${itemLabel} with`}
          onChange={(event) => {
            setSelectedFriendId(event.target.value);
          }}
          value={selectedFriendId}
        >
          {friends.map((friend) => (
            <option key={friend.user.id} value={friend.user.id}>
              {friend.user.display_name}
            </option>
          ))}
        </select>
      </label>
      <button
        className="book-card__button book-card__button--ghost"
        disabled={isSharing || !selectedFriendId}
        onClick={() => {
          void handleShare();
        }}
        type="button"
      >
        {isSharing ? "Sharing..." : "Share"}
      </button>
      {statusMessage ? (
        <p className="library-page__status-copy" role="status">
          {statusMessage}
        </p>
      ) : null}
      {errorMessage ? (
        <p className="library-page__alert" role="alert">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
