---
description: Run our tests, Debug the output, Fix the issues, Repeat. 
---

# Debugging and Fixing Agent Rules

## Core Principle
**Run our tests, Debug the output, Fix the issues, Repeat.**

## Primary Workflow

### 1. Test Execution Phase
- **ALWAYS** run the full test suite before making any changes
- Execute tests in the correct environment (development, staging, production-like)
- Capture complete test output including stdout, stderr, and exit codes
- Document test execution time and resource usage
- Never skip tests due to time constraints - incomplete testing leads to cascading failures

### 2. Debug Analysis Phase
- **Read the entire error output** - don't jump to conclusions from partial information
- Identify the root cause, not just symptoms
- Check error logs in chronological order to understand the failure chain
- Examine stack traces completely, including nested exceptions
- Look for patterns in multiple test failures - they often share common causes
- Verify environment variables, dependencies, and configuration settings
- Check for race conditions, timing issues, or resource constraints

### 3. Fix Implementation Phase
- **Make minimal, targeted changes** - fix the specific issue without over-engineering
- Implement one fix at a time to isolate the impact of each change
- Write clear, descriptive commit messages explaining what was fixed and why
- Add or update tests to prevent regression of the same issue
- Ensure fixes are compatible with existing functionality
- Document any workarounds or limitations in the fix

### 4. Validation Phase
- **Re-run the full test suite** after each fix to ensure nothing broke
- Verify the specific failing test now passes
- Check that no new test failures were introduced
- Run additional integration tests if the fix affects multiple components
- Test edge cases and boundary conditions related to the fix

## Critical Rules

### Never Skip Steps
- Do not proceed to debugging without running tests first
- Do not implement fixes without understanding the root cause
- Do not consider a fix complete without validation testing
- Do not move to the next issue until current issue is fully resolved

### Evidence-Based Debugging
- Always work from actual error messages, not assumptions
- Reproduce issues consistently before attempting fixes
- Use logging and debugging tools rather than guessing
- Document your debugging process for future reference

### Incremental Progress
- Make small, verifiable changes rather than large refactors
- Test each change independently
- Maintain a working state between iterations
- Keep detailed notes of what was tried and what worked

### Communication and Documentation
- Log all debugging steps and findings
- Update issue trackers with progress and solutions
- Document any configuration changes or environment requirements
- Share learnings with the team to prevent similar issues

## Advanced Debugging Strategies

### When Tests Pass Locally But Fail in CI/CD
- Compare environment configurations (OS, versions, dependencies)
- Check for missing environment variables or secrets
- Examine differences in test data or database state
- Look for timing issues in parallel test execution
- Verify resource limits and available memory/CPU

### When Fixing One Issue Breaks Another
- Identify the shared dependencies between failing components
- Check for tight coupling that should be refactored
- Implement feature flags to isolate changes
- Consider the order of operations in initialization or shutdown
- Review interface contracts and API compatibility

### When Issues Are Intermittent
- Implement additional logging to capture failure conditions
- Run tests multiple times to identify patterns
- Check for resource leaks or cleanup issues
- Look for race conditions or timing dependencies
- Monitor system resources during test execution

## Quality Gates

### Before Marking an Issue as Fixed
- [ ] All tests pass consistently (minimum 3 consecutive runs)
- [ ] No new test failures introduced
- [ ] Root cause identified and documented
- [ ] Fix is minimal and targeted
- [ ] Regression tests added where appropriate
- [ ] Code review completed (if working in a team)
- [ ] Documentation updated if needed

### Before Moving to Next Issue
- [ ] Current fix is deployed and verified in target environment
- [ ] Monitoring confirms the issue is resolved
- [ ] Team is notified of the resolution
- [ ] Lessons learned are documented
- [ ] Related issues are checked for similar root causes

## Emergency Protocols

### When Facing Critical Production Issues
1. **Stabilize first** - implement quick fixes to restore service
2. **Document the incident** - capture all relevant information
3. **Follow the normal debugging cycle** for permanent fixes
4. **Conduct post-incident review** to prevent recurrence

### When Debugging Takes Too Long
1. **Reassess the approach** - consider alternative debugging methods
2. **Seek help** - involve other team members or subject matter experts
3. **Implement temporary workarounds** while investigating root cause
4. **Set time limits** for debugging sessions to maintain focus

## Success Metrics

- **Test pass rate**: Aim for 100% test suite success
- **Fix effectiveness**: Issues should not recur after being marked as resolved
- **Debugging efficiency**: Time from issue identification to resolution
- **Code quality**: Fixes should not introduce technical debt
- **Team learning**: Knowledge should be shared and documented

## Remember

The goal is not just to make tests pass, but to build robust, maintainable systems. Each debugging cycle should leave the codebase in a better state than before, with increased confidence in the system's reliability and better understanding of its behavior.

**When in doubt, run the tests again.**