# killswitch/

The billing kill switch (backlog C9, DECISIONS §1): a small Cloud Run function that unlinks billing from its project when a budget notification says spend has crossed the cap.

The agent writes and tests it; the author deploys it from Cloud Shell (`docs/author_setup.md` §2.3), because deploying needs billing permissions agents never hold.
