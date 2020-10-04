# Contributing Guidelines

_(I as the author am aware not all of these are followed, although ideally they are done so.)_

## Testing

-   mypy (static type checking)
-   flake8 (general format linting)
-   pylint (flake8 but more, to check for docstrings and others)
-   black (opinionated but relieves style decision and maintenance)

You can add a pre-commit hook to run all tests and checks by running this:

```bash
git config core.hooksPath hooks
```

You may also want to edit the executable used in the pre-commit hook locally:

```bash
# default
pipenv run mypy project
# specific Python executable (use "which python3" to get the path)
/usr/bin/python3 -m pipenv run mypy project
```

GitHub Actions will also be used to run automated tests on push/PR.

## PR/Commit convention

-   Imperative mood (Verb in simple present tense + object + ...)
    -   Do this
    -   Add tests
    -   Change SQL queries to ORM calls
-   Limit to 50 characters and no period in the subject line or PR title
-   Start with an initial capital letter
-   Append "(Fix #issueno)" in title for issue fixes
-   Append "(#prno)" in title for squash commits and merge commits ("(Fix #issueno)" only needs to be in the PR title then)
-   Please add a body description if there are significant changes (Line length limit: 72 characters, no line limit)
-   Focus on what, why and how in the body description
-   Individual commits should only do small changes

Example:

```
Implement colorblind support

Several modes of colorblind palettes have been added which are
red-green, monotone and grayscale. This is done to aid in accessibility
for the visually impaired...
...
```

## Code convention

-   As much static typing as possible
-   Strict and opinionated black formatter helps to eliminate style worries
-   Always have a docstring (imperative mood, actual documentation with sphinx can be considered if complex enough)
-   Always use descriptive, helpful identifiers
-   Add comments explaining how less straightforward code work
-   Follow PEP8 (should be handled by black)
-   Line length limit: 100 characters (should be handled by black)
-   American English only (colour → color, centre → center, initialise → initialize, analyse → analyze, grey → gray)
