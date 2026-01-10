
import re

# The new regex pattern from WalletService
# Refined to allow more characters and verify length precisely
WALLET_PATTERN = r'^(?:(?:EQ|UQ|kQ|0Q)[A-Za-z0-9_-]{44,50}|-?\d:[a-fA-F0-9]{64})$'

test_addresses = [
    # Valid User-friendly (Base64)
    "EQD6mK_qX5hS7Vj7N0Z6U-y8P_Wd9_n9v8_7m_K_qX5hS1",
    "UQAf-X-qX5hS7Vj7N0Z6U-y8P_Wd9_n9v8_7m_K_qX5hST",
    "kQAf-X-qX5hS7Vj7N0Z6U-y8P_Wd9_n9v8_7m_K_qX5hST",
    
    # Valid Raw (Hex)
    "0:54687d6e6f766100000000000000000000000000000000000000000000000000",
    "-1:54687d6e6f766100000000000000000000000000000000000000000000000000",
    
    # Invalid addresses
    "EQD6mK_qX", # Too short
    "0:54687d",    # Too short hex
    "random_string",
    "1:54687d6e6f766100000000000000000000000000000000000000000000000000", # Wrong workchain (usually 0 or -1)
]

print(f"Testing pattern: {WALLET_PATTERN}\n")

for addr in test_addresses:
    is_valid = bool(re.match(WALLET_PATTERN, addr))
    status = "✅ VALID" if is_valid else "❌ INVALID"
    print(f"{status}: {addr}")
