.. _release-update:

Updating the Release Workflow
=============================

The release workflow is triggered when a release branch (for example,
``release/0.19.2``) is merged into the main branch. It performs the following steps:

#. Validates the pull request.

   This includes that the PR was acutally merged (not just closed)
   and the source branch follows the naming convention ``release/X.Y.Z``.
   It also extracts the semantic version from the branch name for later use.

#. Tagging

   Automatically creates and pushes a new Git tag using the extracted version.

#. Build & publish

   Uses |uv| to build a Python wheel and creates a GitHub Release with
   the build artifact and auto-generated notes.


.. _release-generate-pat:

Generating a New Personal Access Token (PAT)
--------------------------------------------

.. important::

    The workflow uses a Personal Access Token (PAT) with appropriate permissions to push tags and create releases.
    The following steps outline how to generate a new PAT and store it in GitHub Secrets.

In order to execute the release workflow, it needs a PAT. If the PAT is
expired, revoked, or you need to update it for any reason, follow these steps:

.. steps::

   .. step:: Open GitHub settings

      Log in to your GitHub account. Click your avatar icon, then
      :guilabel:`Settings`.

   .. step:: Open classic personal access tokens

      In the left sidebar, click :guilabel:`Developer settings` > :guilabel:`Personal access tokens` > :guilabel:`Tokens (classic)`.

   .. step:: Start creating a classic token

      Click the :guilabel:`Generate new token` button and select
      :guilabel:`Tokens (classic)`. You may need to authenticate if you
      enabled Two Factor Authentication (2FA).

   .. step:: Name the token

      Enter the name ``PAT_DOCBUILD_TOKEN_FOR_TAGS``.

   .. step:: Set the token expiration

      Select an expiration date for the token. It's recommended to set an
      expiration date to enhance security.

   .. step:: Select the required scopes

      Select the scopes ``repo`` and ``workflow`` to allow the token to
      push tags and trigger workflows.

   .. step:: Generate the token

      Click :guilabel:`Generate token`.

   .. step:: Copy and store the token securely

      You won't be able to see the token again after you leave the page, so make sure to save it in a secure location.

.. _release-update-pat-github-secrets:

Updating the PAT in GitHub Secrets
----------------------------------

.. steps::

   .. step:: Open the repository settings

      Go to the https://github.com/openSUSE/docbuild/settings page of the repository.

   .. step:: Open Actions secrets

      In the left sidebar, click :guilabel:`Secrets and variables` > :guilabel:`Actions`.

   .. step:: Add a repository secret

      Click the :guilabel:`New repository secret` button.

   .. step:: Enter the PAT secret

      Enter the name ``PAT_DOCBUILD_TOKEN_FOR_TAGS`` and paste the copied token.

   .. step:: Save the secret

      Finish with :guilabel:`Add secret` to save the new token in GitHub Secrets.
