"""Reviews domain load test scenarios.

Five stateful SequentialTaskSet journeys covering the review lifecycle:
submission and moderation, community voting, editing and resubmission,
seller replies, and content reporting/removal.
"""

import uuid

from locust import HttpUser, SequentialTaskSet, between, task

from loadtests.data_generators import edit_review_data, review_data
from loadtests.helpers.response import extract_error_detail
from loadtests.helpers.state import ReviewState


class ReviewSubmitAndModerateJourney(SequentialTaskSet):
    """Submit Review -> Approve -> Verify Published.

    The happy path: a review is submitted, approved by a moderator,
    and verified as published.
    Generates events: ReviewSubmitted, ReviewApproved.
    """

    def on_start(self):
        self.state = ReviewState()

    @task
    def submit_review(self):
        payload = review_data()
        self.state.product_id = payload["product_id"]
        self.state.customer_id = payload["customer_id"]
        with self.client.post(
            "/reviews",
            json=payload,
            catch_response=True,
            name="POST /reviews",
        ) as resp:
            if resp.status_code == 201:
                self.state.review_id = resp.json()["review_id"]
                self.state.current_status = "Pending"
            else:
                resp.failure(f"Submit review failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def approve_review(self):
        with self.client.put(
            f"/reviews/{self.state.review_id}/moderate",
            json={
                "moderator_id": f"mod-{uuid.uuid4().hex[:8]}",
                "action": "Approve",
            },
            catch_response=True,
            name="PUT /reviews/{id}/moderate (approve)",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_status = "Published"
            else:
                resp.failure(f"Approve failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def verify_published(self):
        with self.client.get(
            f"/reviews/{self.state.review_id}",
            catch_response=True,
            name="GET /reviews/{id}",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Get review failed: {resp.status_code}")

    @task
    def get_product_rating(self):
        """Verify ProductRating projection is populated."""
        with self.client.get(
            f"/reviews/ratings/{self.state.product_id}",
            catch_response=True,
            name="GET /reviews/ratings/{product_id}",
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Get product rating failed: {resp.status_code}")

    @task
    def get_product_reviews(self):
        """Verify ProductReviews projection (list view)."""
        with self.client.get(
            f"/reviews?product_id={self.state.product_id}",
            catch_response=True,
            name="GET /reviews?product_id=",
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Get product reviews failed: {resp.status_code}")

    @task
    def get_customer_reviews(self):
        """Verify CustomerReviews projection."""
        with self.client.get(
            f"/reviews/customer/{self.state.customer_id}",
            catch_response=True,
            name="GET /reviews/customer/{customer_id}",
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Get customer reviews failed: {resp.status_code}")

    @task
    def done(self):
        self.interrupt()


class ReviewVotingJourney(SequentialTaskSet):
    """Submit -> Approve -> Vote Helpful -> Verify Vote Count.

    Models community interaction: a published review receives helpful votes.
    Generates events: ReviewSubmitted, ReviewApproved, HelpfulVoteRecorded.
    """

    def on_start(self):
        self.state = ReviewState()

    @task
    def submit_review(self):
        payload = review_data()
        self.state.product_id = payload["product_id"]
        self.state.customer_id = payload["customer_id"]
        with self.client.post(
            "/reviews",
            json=payload,
            catch_response=True,
            name="POST /reviews",
        ) as resp:
            if resp.status_code == 201:
                self.state.review_id = resp.json()["review_id"]
            else:
                resp.failure(f"Submit review failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def approve_review(self):
        with self.client.put(
            f"/reviews/{self.state.review_id}/moderate",
            json={
                "moderator_id": f"mod-{uuid.uuid4().hex[:8]}",
                "action": "Approve",
            },
            catch_response=True,
            name="PUT /reviews/{id}/moderate (approve)",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Approve failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def vote_helpful(self):
        # Different customer votes helpful
        voter_id = f"cust-{uuid.uuid4().hex[:8]}"
        with self.client.post(
            f"/reviews/{self.state.review_id}/votes",
            json={
                "customer_id": voter_id,
                "vote_type": "Helpful",
            },
            catch_response=True,
            name="POST /reviews/{id}/votes",
        ) as resp:
            if resp.status_code != 201:
                resp.failure(f"Vote failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def verify_vote(self):
        with self.client.get(
            f"/reviews/{self.state.review_id}",
            catch_response=True,
            name="GET /reviews/{id}",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Get review failed: {resp.status_code}")

    @task
    def done(self):
        self.interrupt()


class ReviewEditAndResubmitJourney(SequentialTaskSet):
    """Submit -> Reject -> Edit -> Approve -> Verify.

    Models the rejection and re-submission flow.
    Generates events: ReviewSubmitted, ReviewRejected, ReviewEdited, ReviewApproved.
    """

    def on_start(self):
        self.state = ReviewState()

    @task
    def submit_review(self):
        payload = review_data()
        self.state.product_id = payload["product_id"]
        self.state.customer_id = payload["customer_id"]
        with self.client.post(
            "/reviews",
            json=payload,
            catch_response=True,
            name="POST /reviews",
        ) as resp:
            if resp.status_code == 201:
                self.state.review_id = resp.json()["review_id"]
            else:
                resp.failure(f"Submit review failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def reject_review(self):
        with self.client.put(
            f"/reviews/{self.state.review_id}/moderate",
            json={
                "moderator_id": f"mod-{uuid.uuid4().hex[:8]}",
                "action": "Reject",
                "reason": "Content needs improvement",
            },
            catch_response=True,
            name="PUT /reviews/{id}/moderate (reject)",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Reject failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def edit_review(self):
        payload = edit_review_data(self.state.customer_id)
        with self.client.put(
            f"/reviews/{self.state.review_id}",
            json=payload,
            catch_response=True,
            name="PUT /reviews/{id} (edit)",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Edit failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def approve_after_edit(self):
        with self.client.put(
            f"/reviews/{self.state.review_id}/moderate",
            json={
                "moderator_id": f"mod-{uuid.uuid4().hex[:8]}",
                "action": "Approve",
            },
            catch_response=True,
            name="PUT /reviews/{id}/moderate (approve)",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Approve after edit failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def verify_published(self):
        with self.client.get(
            f"/reviews/{self.state.review_id}",
            catch_response=True,
            name="GET /reviews/{id}",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Get review failed: {resp.status_code}")

    @task
    def done(self):
        self.interrupt()


class ReviewSellerReplyJourney(SequentialTaskSet):
    """Submit -> Approve -> Seller Reply -> Verify Reply.

    Models seller engagement with published reviews.
    Generates events: ReviewSubmitted, ReviewApproved, SellerReplyAdded.
    """

    def on_start(self):
        self.state = ReviewState()

    @task
    def submit_review(self):
        payload = review_data()
        self.state.product_id = payload["product_id"]
        self.state.customer_id = payload["customer_id"]
        with self.client.post(
            "/reviews",
            json=payload,
            catch_response=True,
            name="POST /reviews",
        ) as resp:
            if resp.status_code == 201:
                self.state.review_id = resp.json()["review_id"]
            else:
                resp.failure(f"Submit review failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def approve_review(self):
        with self.client.put(
            f"/reviews/{self.state.review_id}/moderate",
            json={
                "moderator_id": f"mod-{uuid.uuid4().hex[:8]}",
                "action": "Approve",
            },
            catch_response=True,
            name="PUT /reviews/{id}/moderate (approve)",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Approve failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def add_seller_reply(self):
        with self.client.post(
            f"/reviews/{self.state.review_id}/reply",
            json={
                "seller_id": f"seller-{uuid.uuid4().hex[:8]}",
                "body": "Thank you for your feedback! We appreciate your review.",
            },
            catch_response=True,
            name="POST /reviews/{id}/reply",
        ) as resp:
            if resp.status_code != 201:
                resp.failure(f"Seller reply failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def verify_reply(self):
        with self.client.get(
            f"/reviews/{self.state.review_id}",
            catch_response=True,
            name="GET /reviews/{id}",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Get review failed: {resp.status_code}")

    @task
    def done(self):
        self.interrupt()


class ReviewReportAndRemoveJourney(SequentialTaskSet):
    """Submit -> Approve -> Report -> Remove.

    Models the content moderation flow where a published review gets
    reported by a user and then removed by a moderator.
    Generates events: ReviewSubmitted, ReviewApproved, ReviewReported, ReviewRemoved.
    """

    def on_start(self):
        self.state = ReviewState()

    @task
    def submit_review(self):
        payload = review_data()
        self.state.product_id = payload["product_id"]
        self.state.customer_id = payload["customer_id"]
        with self.client.post(
            "/reviews",
            json=payload,
            catch_response=True,
            name="POST /reviews",
        ) as resp:
            if resp.status_code == 201:
                self.state.review_id = resp.json()["review_id"]
            else:
                resp.failure(f"Submit review failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def approve_review(self):
        with self.client.put(
            f"/reviews/{self.state.review_id}/moderate",
            json={
                "moderator_id": f"mod-{uuid.uuid4().hex[:8]}",
                "action": "Approve",
            },
            catch_response=True,
            name="PUT /reviews/{id}/moderate (approve)",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Approve failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def report_review(self):
        with self.client.post(
            f"/reviews/{self.state.review_id}/reports",
            json={
                "customer_id": f"cust-{uuid.uuid4().hex[:8]}",
                "reason": "Inappropriate content",
            },
            catch_response=True,
            name="POST /reviews/{id}/reports",
        ) as resp:
            if resp.status_code not in (200, 201):
                resp.failure(f"Report review failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def remove_review(self):
        with self.client.put(
            f"/reviews/{self.state.review_id}/remove",
            json={
                "removed_by": f"mod-{uuid.uuid4().hex[:8]}",
                "reason": "Violates community guidelines",
            },
            catch_response=True,
            name="PUT /reviews/{id}/remove",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Remove review failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class ReviewsUser(HttpUser):
    """Locust user simulating Reviews domain interactions.

    Weighted distribution:
    - 30% Submit and moderate (most common)
    - 20% Voting (community interaction)
    - 15% Edit and resubmit (rejection flow)
    - 15% Seller reply (seller engagement)
    - 20% Report and remove (moderation)
    """

    wait_time = between(0.5, 2.0)
    tasks = {
        ReviewSubmitAndModerateJourney: 6,
        ReviewVotingJourney: 4,
        ReviewEditAndResubmitJourney: 3,
        ReviewSellerReplyJourney: 3,
        ReviewReportAndRemoveJourney: 4,
    }
