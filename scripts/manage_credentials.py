#!/usr/bin/env python3
"""CLI utility for managing encrypted credentials.

Usage:
    python scripts/manage_credentials.py store instagram username myusername
    python scripts/manage_credentials.py store instagram password
    python scripts/manage_credentials.py get instagram password
    python scripts/manage_credentials.py list
    python scripts/manage_credentials.py delete instagram password
"""

import sys
import getpass
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.credential_manager import get_credential_manager, reset_credential_manager
from src.utils.security import mask_credential


def get_master_password() -> str:
    """Prompt for master password."""
    password = getpass.getpass("Enter master password: ")
    if not password:
        print("Error: Master password cannot be empty")
        sys.exit(1)
    return password


def cmd_store(args, manager):
    """Store a credential."""
    value = args.value

    # If no value provided, prompt securely
    if not value:
        value = getpass.getpass(f"Enter {args.credential_type} for {args.platform}: ")
        if not value:
            print("Error: Value cannot be empty")
            sys.exit(1)

    success = manager.store(args.platform, args.credential_type, value)

    if success:
        print(f"Stored {args.platform}/{args.credential_type}")
    else:
        print(f"Failed to store credential")
        sys.exit(1)


def cmd_get(args, manager):
    """Get a credential."""
    value = manager.get(args.platform, args.credential_type)

    if value:
        if args.show:
            print(value)
        else:
            print(f"{args.platform}/{args.credential_type}: {mask_credential(value, 3)}")
    else:
        print(f"No credential found for {args.platform}/{args.credential_type}")
        sys.exit(1)


def cmd_delete(args, manager):
    """Delete a credential."""
    success = manager.delete(args.platform, args.credential_type)

    if success:
        print(f"Deleted {args.platform}/{args.credential_type}")
    else:
        print(f"Failed to delete credential (may not exist)")


def cmd_list(args, manager):
    """List all stored credentials."""
    credentials = manager.list_credentials()

    if not credentials:
        print("No credentials stored")
        return

    print("Stored credentials:")
    for key, masked_value in sorted(credentials.items()):
        print(f"  {key}: {masked_value}")


def cmd_store_platform(args, manager):
    """Store all credentials for a platform interactively."""
    platform = args.platform

    print(f"Setting up credentials for {platform}")
    print("-" * 40)

    # Determine which credentials to ask for based on platform
    if platform in ["facebook", "linkedin"]:
        email = input("Email (press Enter to skip): ").strip() or None
        password = getpass.getpass("Password (press Enter to skip): ") or None
        username = None
    else:  # instagram, twitter
        username = input("Username (press Enter to skip): ").strip() or None
        password = getpass.getpass("Password (press Enter to skip): ") or None
        email = None

    # Google auth for Twitter
    google_email = None
    google_password = None
    if platform == "twitter":
        use_google = input("Use Google authentication? (y/N): ").strip().lower() == 'y'
        if use_google:
            google_email = input("Google email: ").strip() or None
            google_password = getpass.getpass("Google password: ") or None

    # Store credentials
    stored = []
    if username:
        manager.store(platform, "username", username)
        stored.append("username")
    if email:
        manager.store(platform, "email", email)
        stored.append("email")
    if password:
        manager.store(platform, "password", password)
        stored.append("password")
    if google_email:
        manager.store(platform, "google_email", google_email)
        stored.append("google_email")
    if google_password:
        manager.store(platform, "google_password", google_password)
        stored.append("google_password")

    if stored:
        print(f"\nStored: {', '.join(stored)}")
    else:
        print("\nNo credentials stored")


def cmd_verify(args, manager):
    """Verify stored credentials can be decrypted."""
    try:
        credentials = manager._load_encrypted_credentials()
        print(f"Verified: {len(credentials)} credentials accessible")
        return True
    except Exception as e:
        print(f"Verification failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Manage encrypted credentials for Comment Extractor"
    )
    parser.add_argument(
        "--keyring", action="store_true",
        help="Use OS keyring instead of encrypted file"
    )
    parser.add_argument(
        "--storage-path", type=Path,
        help="Path to credential storage directory"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Store command
    store_parser = subparsers.add_parser("store", help="Store a credential")
    store_parser.add_argument("platform", help="Platform name (instagram, facebook, etc.)")
    store_parser.add_argument("credential_type", help="Credential type (password, username, email)")
    store_parser.add_argument("value", nargs="?", help="Value (will prompt if not provided)")

    # Get command
    get_parser = subparsers.add_parser("get", help="Get a credential")
    get_parser.add_argument("platform", help="Platform name")
    get_parser.add_argument("credential_type", help="Credential type")
    get_parser.add_argument("--show", action="store_true", help="Show full value (not masked)")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a credential")
    delete_parser.add_argument("platform", help="Platform name")
    delete_parser.add_argument("credential_type", help="Credential type")

    # List command
    subparsers.add_parser("list", help="List all stored credentials")

    # Setup platform command
    setup_parser = subparsers.add_parser("setup", help="Setup all credentials for a platform")
    setup_parser.add_argument("platform", help="Platform name")

    # Verify command
    subparsers.add_parser("verify", help="Verify credentials can be decrypted")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Get master password (not needed for keyring)
    master_password = None
    if not args.keyring and args.command not in ["verify"]:
        master_password = get_master_password()

    # Initialize credential manager
    manager = get_credential_manager(
        storage_path=args.storage_path,
        use_keyring=args.keyring,
        master_password=master_password
    )

    # Execute command
    if args.command == "store":
        cmd_store(args, manager)
    elif args.command == "get":
        cmd_get(args, manager)
    elif args.command == "delete":
        cmd_delete(args, manager)
    elif args.command == "list":
        cmd_list(args, manager)
    elif args.command == "setup":
        cmd_store_platform(args, manager)
    elif args.command == "verify":
        # Need password for verify
        if not args.keyring:
            master_password = get_master_password()
            manager.set_master_password(master_password)
        cmd_verify(args, manager)


if __name__ == "__main__":
    main()
