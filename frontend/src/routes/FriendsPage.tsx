import { useEffect, useState } from "react";

import {
  acceptFriendRequest,
  acceptShare,
  declineFriendRequest,
  declineShare,
  getFriendsDirectory,
  getFriendsOverview,
  getSharesOverview,
  sendFriendRequest,
  unfriendUser,
} from "../api/client";
import type {
  DirectoryEntryRecord,
  FriendsOverviewRecord,
  SharedItemRecord,
  SharesOverviewRecord,
} from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { PersonAvatar } from "../components/PersonAvatar";

type FriendsPageProps = {
  onNavigate: (pathname: string) => void;
};

const EMPTY_OVERVIEW: FriendsOverviewRecord = {
  friends: [],
  incoming_requests: [],
  outgoing_requests: [],
};

const EMPTY_SHARES: SharesOverviewRecord = {
  incoming: [],
  outgoing: [],
};

function shareItemTypeLabel(share: SharedItemRecord) {
  return share.item_type === "document" ? "Book" : "Voice preset";
}

export function FriendsPage({ onNavigate }: FriendsPageProps) {
  const [overview, setOverview] = useState<FriendsOverviewRecord>(EMPTY_OVERVIEW);
  const [shares, setShares] = useState<SharesOverviewRecord>(EMPTY_SHARES);
  const [directory, setDirectory] = useState<DirectoryEntryRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const refresh = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [nextOverview, nextShares, nextDirectory] = await Promise.all([
        getFriendsOverview(),
        getSharesOverview(),
        getFriendsDirectory(),
      ]);
      setOverview(nextOverview);
      setShares(nextShares);
      setDirectory(nextDirectory);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load friends");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const runAction = async (action: () => Promise<unknown>, successMessage: string | null = null) => {
    setActionError(null);
    setStatusMessage(null);
    try {
      await action();
      if (successMessage) {
        setStatusMessage(successMessage);
      }
      await refresh();
    } catch (responseError) {
      setActionError(responseError instanceof Error ? responseError.message : "Unable to update friends");
    }
  };

  const pendingIncomingShares = shares.incoming.filter((share) => share.status === "pending");
  const respondedIncomingShares = shares.incoming.filter((share) => share.status !== "pending");

  return (
    <section aria-label="Friends page" className="library-page friends-page">
      <div className="library-page__hero">
        <div className="library-page__title-block">
          <p className="library-page__eyebrow">Friends</p>
          <h2>Friends and sharing</h2>
          <p>
            Share books and cloned narrators with other readers on this host. Shares arrive as offers, and
            accepting one adds your own independent copy.
          </p>
        </div>
      </div>

      {isLoading ? <p className="library-page__status-copy">Loading friends...</p> : null}
      {error ? (
        <p className="library-page__alert" role="alert">
          {error}
        </p>
      ) : null}
      {actionError ? (
        <p className="library-page__alert" role="alert">
          {actionError}
        </p>
      ) : null}
      {statusMessage ? (
        <p className="library-page__status-copy" role="status">
          {statusMessage}
        </p>
      ) : null}

      <section className="settings-page__preferences-panel" aria-label="Share inbox">
        <div className="settings-page__panel-header">
          <div>
            <p className="library-page__eyebrow">Share inbox</p>
            <h3>Offers waiting for you</h3>
          </div>
        </div>
        {pendingIncomingShares.length === 0 ? (
          <EmptyState
            copy="No pending shares right now. Books and narrators friends send you will appear here."
            icon="collections"
            title="Inbox is clear"
          />
        ) : (
          <ul className="library-page__summary friends-page__list">
            {pendingIncomingShares.map((share) => (
              <li className="friends-page__row" key={share.id}>
                <span>
                  {shareItemTypeLabel(share)}: <strong>{share.item_label}</strong> from{" "}
                  {share.other_user.display_name}
                  {share.message ? ` — “${share.message}”` : ""}
                </span>
                <span className="friends-page__row-actions">
                  <button
                    className="book-card__button"
                    onClick={() => {
                      void runAction(
                        () => acceptShare(share.id),
                        `Added ${share.item_label} to your ${share.item_type === "document" ? "library" : "voices"}.`,
                      );
                    }}
                    type="button"
                  >
                    Accept
                  </button>
                  <button
                    className="book-card__button book-card__button--ghost"
                    onClick={() => {
                      void runAction(() => declineShare(share.id));
                    }}
                    type="button"
                  >
                    Decline
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
        {respondedIncomingShares.length > 0 ? (
          <ul className="library-page__summary friends-page__list">
            {respondedIncomingShares.map((share) => (
              <li key={share.id}>
                {shareItemTypeLabel(share)}: {share.item_label} from {share.other_user.display_name} •{" "}
                {share.status}
                {share.status === "accepted" && share.item_type === "document" && share.accepted_item_id ? (
                  <button
                    className="book-card__button book-card__button--ghost"
                    onClick={() => {
                      onNavigate(`/books/${share.accepted_item_id}`);
                    }}
                    type="button"
                  >
                    Open book
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="settings-page__preferences-panel" aria-label="Friend requests">
        <div className="settings-page__panel-header">
          <div>
            <p className="library-page__eyebrow">Requests</p>
            <h3>Friend requests</h3>
          </div>
        </div>
        {overview.incoming_requests.length === 0 && overview.outgoing_requests.length === 0 ? (
          <p className="library-page__status-copy">No open friend requests.</p>
        ) : (
          <ul className="library-page__summary friends-page__list">
            {overview.incoming_requests.map((request) => (
              <li className="friends-page__row" key={request.friendship_id}>
                <span>{request.user.display_name} wants to be friends</span>
                <span className="friends-page__row-actions">
                  <button
                    className="book-card__button"
                    onClick={() => {
                      void runAction(() => acceptFriendRequest(request.friendship_id));
                    }}
                    type="button"
                  >
                    Accept
                  </button>
                  <button
                    className="book-card__button book-card__button--ghost"
                    onClick={() => {
                      void runAction(() => declineFriendRequest(request.friendship_id));
                    }}
                    type="button"
                  >
                    Decline
                  </button>
                </span>
              </li>
            ))}
            {overview.outgoing_requests.map((request) => (
              <li key={request.friendship_id}>
                Waiting on {request.user.display_name} to answer your request
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="settings-page__preferences-panel" aria-label="Your friends">
        <div className="settings-page__panel-header">
          <div>
            <p className="library-page__eyebrow">Friends</p>
            <h3>Your friends</h3>
          </div>
        </div>
        {overview.friends.length === 0 ? (
          <EmptyState
            copy="No friends yet. Add someone from the directory below to start sharing."
            icon="friends"
            title="No friends yet"
          />
        ) : (
          <ul className="library-page__summary friends-page__list">
            {overview.friends.map((friend) => (
              <li className="friends-page__row" key={friend.friendship_id}>
                <span className="person-row__identity">
                  <PersonAvatar displayName={friend.user.display_name} />
                  <span>
                    {friend.user.display_name} ({friend.user.username})
                  </span>
                </span>
                <button
                  className="book-card__button book-card__button--ghost"
                  onClick={() => {
                    void runAction(() => unfriendUser(friend.user.id));
                  }}
                  type="button"
                >
                  Unfriend
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="settings-page__preferences-panel" aria-label="People on this host">
        <div className="settings-page__panel-header">
          <div>
            <p className="library-page__eyebrow">Directory</p>
            <h3>People on this host</h3>
          </div>
        </div>
        {directory.length === 0 ? (
          <p className="library-page__status-copy">No other readers on this host yet.</p>
        ) : (
          <ul className="library-page__summary friends-page__list">
            {directory.map((entry) => (
              <li className="friends-page__row" key={entry.user.id}>
                <span className="person-row__identity">
                  <PersonAvatar displayName={entry.user.display_name} />
                  <span>
                    {entry.user.display_name} ({entry.user.username})
                  </span>
                </span>
                {entry.state === "none" ? (
                  <button
                    className="book-card__button"
                    onClick={() => {
                      void runAction(() => sendFriendRequest(entry.user.id), "Friend request sent.");
                    }}
                    type="button"
                  >
                    Add friend
                  </button>
                ) : (
                  <span className="library-page__status-copy">
                    {entry.state === "friends"
                      ? "Friends"
                      : entry.state === "pending_outgoing"
                        ? "Request sent"
                        : "Awaiting your answer above"}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
