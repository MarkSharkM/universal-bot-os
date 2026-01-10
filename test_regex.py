import re

# Updated regex from WalletService
WALLET_PATTERN_DEFAULT = r'^(?:(?:EQ|UQ|kQ|0Q)[A-Za-z0-9_+\/-]{44,50}|(?:-?1|0):[a-fA-F0-9]{64})$'

valid_wallets = [
    "EQCD39VS5jcptHL8vMjEXrzGaRcCVYto7HUn4bpAOg8xqB2N",  # Standard
    "UQCD39VS5jcptHL8vMjEXrzGaRcCVYto7HUn4bpAOg8xqEbi",  # URL-safe
    "0:85cf0698ca28bd1dd02a02c2ac5bb4f65529939c64165600402a7f6f74842183",  # Logic failure case (Raw Hex from logs)
    "0:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",  # Raw Hex 0:
    "-1:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef", # Raw Hex -1:
    "kQCD39VS5jcptHL8vMjEXrzGaRcCVYto7HUn4bpAOg8xqD2_",  # Testnet
]

invalid_wallets = [
    "EQCD39VS5jcptHL8vMjEXrzGaRcCVYto7HUn4bpAOg8xq",     # Too short
    "EQCD39VS5jcptHL8vMjEXrzGaRcCVYto7HUn4bpAOg8xqB2N_TOO_LONG_123", # Too long
    "InvalidWalletStringWithForbiddenChars!",             # Invalid chars
    "0:shorthex",                                         # Raw hex too short
    "0:zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz", # Invalid hex chars
]

print(f"Testing regex: {WALLET_PATTERN_DEFAULT}")
print("-" * 50)

all_passed = True

print("Validating EXPECTED VALID wallets:")
for w in valid_wallets:
    match = re.match(WALLET_PATTERN_DEFAULT, w)
    status = "✅ PASS" if match else "❌ FAIL"
    if not match: all_passed = False
    print(f"[{status}] {w[:20]}...")

print("-" * 50)
print("Validating EXPECTED INVALID wallets:")
for w in invalid_wallets:
    match = re.match(WALLET_PATTERN_DEFAULT, w)
    status = "✅ PASS" if not match else "❌ FAIL (Should be invalid)"
    if match: all_passed = False
    print(f"[{status}] {w[:20]}...")

if all_passed:
    print("\n✨ ALL TESTS PASSED")
else:
    print("\n💥 SOME TESTS FAILED")
    exit(1)
