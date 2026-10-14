"""Command Line Interface for BARSA — Universal AI Memory Infrastructure."""

import argparse
import logging
import sys

from barsa.core.config import get_settings
from barsa.mcp.server import create_mcp_server


def setup_cli_logging(_stdio_mode: bool = False, debug: bool = False) -> None:
    """Configure logging to stderr to keep stdout 100% clean for stdio protocol messages."""
    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # Remove existing handlers to prevent accidental writes to stdout
    root_logger.handlers = [handler]


def run_mcp_server(args: argparse.Namespace) -> None:
    """Launch the Barsa Model Context Protocol (MCP) server."""
    transport = args.transport.lower()
    is_stdio = transport == "stdio"
    setup_cli_logging(_stdio_mode=is_stdio, debug=args.debug)

    settings = get_settings()
    server = create_mcp_server(settings)

    if not is_stdio:
        sys.stderr.write(f"Starting Barsa MCP server on {args.host}:{args.port} using transport '{transport}'...\n")

    if transport == "stdio":
        server.run(transport="stdio")
    elif transport in ("streamable-http", "http"):
        server.run(transport="streamable-http", host=args.host, port=args.port)
    elif transport == "sse":
        server.run(transport="sse", host=args.host, port=args.port)
    else:
        sys.stderr.write(f"Unsupported transport '{transport}'. Choose 'stdio', 'streamable-http', or 'sse'.\n")
        sys.exit(1)


def run_api_server(args: argparse.Namespace) -> None:
    """Launch the FastAPI REST API server."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "barsa.main:app", host=args.host, port=args.port, reload=args.reload, log_level=settings.log_level.lower()
    )


def print_info(_args: argparse.Namespace) -> None:
    """Print system configuration and version details."""
    settings = get_settings()
    print("=" * 60)
    print(f"BARSA — Universal AI Memory Infrastructure (v{settings.app_version})")
    print("=" * 60)
    print(f"Environment:       {settings.environment.value}")
    print(f"Data Directory:    {settings.data_dir}")
    print(f"Database Path:     {settings.db_path}")
    print(f"Storage Provider:  {settings.storage_provider.value}")
    print(f"Graph Enabled:     {settings.graph_enabled}")
    print(f"FalkorDB Host:     {settings.falkordb_host}:{settings.falkordb_port}")
    print("=" * 60)


def main() -> None:
    """CLI entry point for the barsa command."""
    parser = argparse.ArgumentParser(
        prog="barsa",
        description="BARSA — Universal AI Memory and Collaboration Infrastructure CLI",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: barsa info
    info_parser = subparsers.add_parser("info", help="Display system information and configuration")
    info_parser.set_defaults(func=print_info)

    # Command: barsa api
    api_parser = subparsers.add_parser("api", help="Run the FastAPI REST server")
    api_parser.add_argument("--host", default="127.0.0.1", help="Host address to bind (default: 127.0.0.1)")
    api_parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    api_parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    api_parser.set_defaults(func=run_api_server)

    # Command: barsa mcp [serve]
    mcp_parser = subparsers.add_parser("mcp", help="Manage and run the MCP server")
    mcp_sub = mcp_parser.add_subparsers(dest="mcp_command", help="MCP subcommands")

    serve_parser = mcp_sub.add_parser("serve", help="Start the MCP server")
    serve_parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="MCP transport protocol (default: stdio)",
    )
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host address (for http/sse transports)")
    serve_parser.add_argument("--port", type=int, default=8001, help="Port (for http/sse transports)")
    serve_parser.set_defaults(func=run_mcp_server)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help(sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
