This is a tool for diffing long strings. It helps when you have to physically transcribe a long string (e.g. a token) from one box to another, which comes up surprisingly often when I'm using Qubes. The intended usage contexts are:

1) Airgapped systems
2) Low-privilege systems without e.g. email access.

But in general it is useful whenever you have two copies of a string, on two devices, and you want to quickly determine whether they are identical (and efficiently find and correct any differences).

You run `diffseek` on both devices, enter the reference string on the first device, enter your best-effort transcription into the second device, then compare a series of generated values across devices, indicating when they match or don't. These are used by `diffseek` to conduct a binary search for differences between the two strings. At every step the string is printed out, with any potentially differing regions written in orange.

For example:
* Maybe you receive a login link for an online account by email, but you want to use the link on a different computer which has no email access.
* You might copy the link by hand. However, this is error-prone, especially with the long hex string likely included in the URL.
* In such a case, you'll start by running `diffseek` on both devices.
    * On the first device, you paste the string in (this happens interactively, keeping your secret value out of your shell history).
    * The string is hashed and some values are derived: a phrase, a color, etc. These are all derived from the hash. All of these are printed out in a single row.
    * On the second device, make your best attempt to copy the string over. This device will hash this string and derive values from it as well.
    * Then, on both devices, press Enter. This triggers diff mode, where differences are identified via binary search.
        * In diff mode, the tool firsts reports the length of your string, and then asks if you would like to target a different length, allowing you to input it if so.
        * Then, a binary search is started. First, the first half of the string (measuring from the target, not actual, length) is hashed and values are derived or shown. Then the user indicates whether these values match the ones seen on the other system.
        * Whenever two hashes match, this indicates that the hashed area is free of errors. By binary search we can narrow down the positions of potential errors.
        * At every step, we can re-print the user-provided string, with sections colored differently by whether they're possible errors (orange), definite errors (red), or known-good (white).
        * We order the search breadth-first so that we can quickly rule out large matching regions of each string.
        * There should be an option to restart the search, which would be useful after we fix an error.

DISCLOSURE: I wrote the description above and provided it to Claude Code, which wrote the corresponding implementation and test suite. I fixed a couple mistakes it made, tested it manually and found it to work as expected for my use case. Still, it is primarily an AI-written tool, if you care about that.

Usage: `./diffseek.py` or `python3 diffseek.py`

Note: The above comment about BFS is now only true when both strings have target length; if the transcribed string has a different length then we want to prioritize finding the first difference, not all differences, for obvious reasons, and so we use DFS instead in this case.
