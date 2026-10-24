import pytest

from docbuild.models.repo import Repo


# Use different spellings/casings of the same URL to test normalization
@pytest.fixture(
    params=["https://github.com/org/repo.git", "https://GitHub.com/ORG/repo.git"]
)
def repo_url(request) -> str:
    return request.param


@pytest.mark.parametrize(
    "input_value, name, url",
    [
        # 1
        (
            "https://github.com/org/repo.git",
            "org/repo",
            "https://github.com/org/repo.git",
        ),
        # 2
        ("https://github.com/ORG/repo", "org/repo", "https://github.com/org/repo.git"),
        # 3
        ("https://github.com/org/repo", "org/repo", "https://github.com/org/repo.git"),
        # 4
        ("https://github.com/org/repo/", "org/repo", "https://github.com/org/repo.git"),
        # 5
        (
            "https://github.com/ORG/repo_git.git/",
            "org/repo_git",
            "https://github.com/org/repo_git.git",
        ),
        # 6
        (
            "https://GitHub.com/ORG/repo_git.git/",
            "org/repo_git",
            "https://github.com/org/repo_git.git",
        ),
        # 7
        ("http://a.b/org/c.git", "org/c", "http://a.b/org/c.git"),
    ],
)
def test_repo_https(input_value, name, url):
    repo = Repo(input_value)
    assert repo.name == name
    assert repo.url == url


@pytest.mark.parametrize(
    "input_value, name, url",
    [
        # 1
        ("git@github.com:org/repo.git", "org/repo", "https://github.com/org/repo.git"),
        # 2
        ("git@github.com:ORG/repo.git", "org/repo", "https://github.com/org/repo.git"),
        # 3
        ("git@github.com:org/repo", "org/repo", "https://github.com/org/repo.git"),
        # 4
        ("git@github.com:org/repo/", "org/repo", "https://github.com/org/repo.git"),
        # 5
        (
            "git@github.com:org/repo_git/",
            "org/repo_git",
            "https://github.com/org/repo_git.git",
        ),
        # 6
        (
            "git@GitHub.com:org/repo_git/",
            "org/repo_git",
            "https://github.com/org/repo_git.git",
        ),
    ],
)
def test_repo_ssh(input_value, name, url):
    repo = Repo(input_value)
    assert repo.name == name
    assert repo.url == url


@pytest.mark.parametrize(
    "input_value, name, url",
    [
        # 1
        ("gh://org/repo", "org/repo", "https://github.com/org/repo.git"),
        # 2
        ("gh://ORG/repo", "org/repo", "https://github.com/org/repo.git"),
        # 3
        ("gh://org/repo/", "org/repo", "https://github.com/org/repo.git"),
        # 4
        ("gh://org/repo.git", "org/repo", "https://github.com/org/repo.git"),
        # 5
        (
            "gh://ORG/repo_git.git",
            "org/repo_git",
            "https://github.com/org/repo_git.git",
        ),
    ],
)
def test_repo_abbreviation(input_value, name, url):
    repo = Repo(input_value)
    assert repo.name == name
    assert repo.url == url


@pytest.mark.parametrize(
    "input_value, surl",
    [
        # 1
        ("https://github.com/org/repo.git", "gh://org/repo"),
        # 2
        ("https://gitlab.com/ORG/repo.git", "gl://org/repo"),
        # 3
        ("git@github.com:org/repo.git", "gh://org/repo"),
        # 4
        ("gh://org/repo", "gh://org/repo"),
        # 5
        ("gh://ORG/repo", "gh://org/repo"),
        # 6
        ("gh://org/repo/", "gh://org/repo"),
        # 7
        ("gh://org/repo.git", "gh://org/repo"),
        # 8
        ("gh://ORG/repo_git.git", "gh://org/repo_git"),
        # 9
        ("GH://ORG/repo_git.git", "gh://org/repo_git"),
    ],
)
def test_repo_with_surl(input_value, surl):
    repo = Repo(input_value)
    assert repo.surl == surl


def test_repo_with_unknown_abbreviation():
    with pytest.raises(ValueError):
        Repo("fake://org/repo")


@pytest.mark.parametrize(
    "input_value, name, url",
    [
        # 1
        ("org/repo", "org/repo", "https://github.com/org/repo.git"),
        # 2
        ("ORG/repo", "org/repo", "https://github.com/org/repo.git"),
        # 3
        ("org/repo_git.git", "org/repo_git", "https://github.com/org/repo_git.git"),
        # 4
    ],
)
def test_repo_abbreviated(input_value, name, url):
    repo = Repo(input_value)
    assert repo.name == name
    assert repo.url == url


@pytest.mark.parametrize(
    "input_value, name, branch, expected_surl, expected_tree",
    [
        # 1
        (
            "org/repo@main",
            "org/repo",
            "main",
            "gh://org/repo@main",
            "https://github.com/org/repo/tree/main",
        ),
        # 2
        (
            "ORG/repo@develop",
            "org/repo",
            "develop",
            "gh://org/repo@develop",
            "https://github.com/org/repo/tree/develop",
        ),
        # 3
        (
            "org/repo_git.git@v1.2.4",
            "org/repo_git",
            "v1.2.4",
            "gh://org/repo_git@v1.2.4",
            "https://github.com/org/repo_git/tree/v1.2.4",
        ),
        # 4
    ],
)
def test_repo_with_branch(input_value, name, branch, expected_surl, expected_tree):
    repo = Repo(input_value)
    assert repo.name == name
    assert repo.branch == branch
    assert repo.surl == expected_surl
    assert repo.treeurl == expected_tree
    assert repo.origin == input_value


def test_repo_with_empty_value():
    with pytest.raises(ValueError):
        Repo("")


def test_repo_with_invalid_value():
    with pytest.raises(ValueError):
        Repo("invalid-repo-value")


def test_repo_compare_with_eq(repo_url):
    repo1 = Repo(repo_url)
    repo2 = Repo("https://github.com/ORG/repo.git")
    assert repo1 == repo2
    assert "org/repo" == repo1
    assert object() != repo1


def test_repo_init_from_repo_without_reparsing(monkeypatch):
    """Verify that initializing from a Repo object avoids re-parsing."""

    # Create the original Repo objects from strings FIRST.
    original = Repo("gh://org/repo@develop")
    original_no_branch = Repo("gh://org/repo")
    original_with_branch = Repo("opensuse/docbuild@main")
    original_again = Repo("gh://org/repo@develop")

    with monkeypatch.context() as m:
        m.setattr(
            Repo,
            "_consolidate_match",
            lambda *_args: pytest.fail("Repo input should not be reparsed"),
        )

        # Now, test the Repo-from-Repo initializations

        # Case 1: Simple copy
        copy = Repo(original)
        assert copy == original
        for attribute in ("url", "treeurl", "surl", "name", "branch", "origin"):
            assert getattr(copy, attribute) == getattr(original, attribute)

        # Case 2: Set branch on a repo that has none
        copy_with_branch = Repo(original_no_branch, default_branch="develop")
        assert copy_with_branch.branch == "develop"
        assert copy_with_branch.surl == "gh://org/repo@develop"
        assert copy_with_branch.treeurl == "https://github.com/org/repo/tree/develop"

        # Case 3: Override existing branch
        copy_override = Repo(original_with_branch, default_branch="v1")
        assert copy_override.branch == "v1"
        assert copy_override.surl == "gh://opensuse/docbuild@v1"

        # Case 4: Same branch should not trigger any change
        copy_again = Repo(original_again, default_branch="develop")
        assert copy_again.branch == "develop"
        assert copy_again.surl == "gh://org/repo@develop"


def test_repo_init_from_string_with_branch():
    """Verify string parsing with default_branch."""
    # Case 1: Use default_branch when parsing a name
    r = Repo("opensuse/docbuild", default_branch="v1")
    assert r.branch == "v1"
    assert r.surl == "gh://opensuse/docbuild@v1"
    assert r.treeurl == "https://github.com/opensuse/docbuild/tree/v1"

    # Case 2: default_branch should not override explicit branch in string
    r2 = Repo("opensuse/docbuild@main", default_branch="v1")
    assert r2.branch == "main"
    assert r2.surl == "gh://opensuse/docbuild@main"


def test_repo_compare_with_in(repo_url):
    repo = Repo(repo_url)
    assert "org/repo" in repo
    assert object() not in repo  # type: ignore


def test_repo_hash(repo_url):
    repo = Repo(repo_url)
    assert hash(repo) == hash(repo.name)


def test_repo_slug(repo_url):
    repo = Repo(repo_url)
    assert repo.slug == "https___github_com_org_repo_git"


def test_repo_surl(repo_url):
    repo = Repo(repo_url)
    assert repo.surl == "gh://org/repo"


def test_repo_str(repo_url):
    repo = Repo(repo_url)
    assert str(repo) == repo_url.lower()
