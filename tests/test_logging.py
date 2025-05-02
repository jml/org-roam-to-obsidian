"""Tests for the logging module."""

import io
import json
import logging

import pytest
import structlog

from org_roam_to_obsidian.logging import get_logger, setup_logging


@pytest.fixture
def captured_log():
    """Capture log output and reset logging after the test."""
    # Create a string IO for capturing logs
    log_output = io.StringIO()

    # Create a handler that writes to our string IO
    handler = logging.StreamHandler(log_output)

    # Get the root logger and add our handler
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)  # Ensure all logs are captured

    # Clear any existing structlog configuration
    structlog.reset_defaults()

    # Yield the string IO for the test to use
    yield log_output

    # Clean up
    root_logger.removeHandler(handler)
    handler.close()
    structlog.reset_defaults()


class TestLogging:
    """Tests for the logging module."""

    def test_json_output_in_normal_mode(self, captured_log):
        """Normal mode produces JSON formatted logs."""
        # Configure logging to output JSON format
        setup_logging(verbose=False)

        # Create and use a logger to generate a log message
        logger = get_logger("test")
        logger.info("test_event", foo="bar")

        # Get the logged output
        output = captured_log.getvalue().strip()

        # Check if we have any output
        assert output, "No log output was captured"

        # Should be valid JSON (might have multiple lines if other loggers are active)
        for line in output.splitlines():
            if "test_event" in line:
                log_data = json.loads(line)

                # Verify expected fields
                assert log_data["event"] == "test_event"
                assert log_data["foo"] == "bar"
                assert "level" in log_data
                assert "timestamp" in log_data
                # Test passed if we found and validated our log
                break
        else:
            # If we don't break out of the loop, our test log wasn't found
            pytest.fail("Could not find our test log message in the output")

    def test_dev_output_in_verbose_mode(self, captured_log):
        """Verbose mode uses the dev console renderer with colors."""
        # Setup in verbose mode
        setup_logging(verbose=True)

        # Since dev renderer outputs colors which are hard to test,
        # just verify the processor chain contains ConsoleRenderer
        processors = structlog.get_config()["processors"]
        assert any(p.__class__.__name__ == "ConsoleRenderer" for p in processors)

    def test_structured_context_is_included(self, captured_log):
        """Logger includes structured context in log output."""
        # Setup in non-verbose mode for JSON output
        setup_logging(verbose=False)

        # Log with structured context
        logger = get_logger("test")
        logger.info(
            "process_completed", duration_ms=150, items_processed=42, status="success"
        )

        # Get the output
        output = captured_log.getvalue().strip()
        assert output, "No log output was captured"

        # Process each line to find our log
        for line in output.splitlines():
            if "process_completed" in line:
                # Parse the JSON log entry
                log_data = json.loads(line)

                # Check all context was included
                assert log_data["event"] == "process_completed"
                assert log_data["duration_ms"] == 150
                assert log_data["items_processed"] == 42
                assert log_data["status"] == "success"
                # Test passed if we found and validated our log
                break
        else:
            pytest.fail("Could not find our test log message in the output")
