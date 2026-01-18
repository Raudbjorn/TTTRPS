# Spec-Driven Development for LLMs

This document provides everything an LLM needs to apply spec-driven development methodology. Follow this systematic three-phase process to transform feature ideas into well-structured implementations.

---

## Overview

Spec-driven development uses three phases to systematically develop features:

1. **Requirements** - Transform vague ideas into clear, testable requirements using EARS format
2. **Design** - Create comprehensive technical architecture and component specifications
3. **Tasks** - Break down design into sequenced, actionable implementation steps

Each phase must be completed and approved before moving to the next. This ensures clarity, reduces rework, and produces maintainable code.

---

## Phase 1: Requirements

### Purpose
Transform a feature idea into structured, testable requirements that all stakeholders understand.

### Process

1. **Analyze the Feature Idea**
   - Break down the core concept into user-facing functionality
   - Identify user roles who will interact with the feature
   - Consider the complete user journey

2. **Create User Stories**
   ```
   As a [role/user type], I want [desired functionality], so that [benefit/value].
   ```

3. **Write Acceptance Criteria using EARS Format**

   EARS (Easy Approach to Requirements Syntax) patterns:

   | Pattern | Use When | Example |
   |---------|----------|---------|
   | **WHEN...THEN** | Event triggers response | WHEN user clicks submit THEN system SHALL validate form |
   | **IF...THEN** | Condition must be met | IF user is authenticated THEN system SHALL display dashboard |
   | **WHILE...SHALL** | Continuous behavior | WHILE upload is in progress system SHALL display progress |
   | **WHERE...SHALL** | Context-specific | WHERE application runs on mobile system SHALL use touch gestures |

   Always use **SHALL** for mandatory behavior.

4. **Cover All Scenarios**
   - Happy path (normal operation)
   - Edge cases (boundary conditions)
   - Error cases (what happens when things go wrong)

### Requirements Document Structure

```markdown
# Requirements: [Feature Name]

## Introduction
[2-3 paragraphs explaining the feature, problem it solves, and business value]

## Requirements

### Requirement 1: [Title]
**User Story:** As a [role], I want [feature], so that [benefit].

#### Acceptance Criteria
1. WHEN [event] THEN system SHALL [response]
2. IF [condition] THEN system SHALL [behavior]
3. WHEN [error condition] THEN system SHALL [error handling]

### Requirement 2: [Title]
[Continue pattern...]

## Non-Functional Requirements
- Performance: WHEN [load] THEN system SHALL [performance criteria]
- Security: IF [security event] THEN system SHALL [security response]

## Constraints and Assumptions
[List technical and business constraints, assumptions made]
```

### Requirements Quality Checklist

Before proceeding to Design:
- [ ] Each requirement is testable and measurable
- [ ] Requirements cover normal, edge, and error cases
- [ ] User stories provide clear business value
- [ ] No vague terms ("fast", "user-friendly", "easy")
- [ ] No implementation details (HOW vs WHAT)
- [ ] All user roles are addressed
- [ ] Requirements don't conflict with each other
- [ ] EARS format is consistent throughout

### Common Pitfalls

| Problem | Bad Example | Good Example |
|---------|-------------|--------------|
| Vague | "System should be fast" | "WHEN user requests data THEN system SHALL respond within 2 seconds" |
| Implementation detail | "System shall use Redis" | "WHEN user requests frequently accessed data THEN system SHALL return cached results" |
| Untestable | "System should be user-friendly" | "WHEN new user completes onboarding THEN system SHALL require no more than 3 clicks to reach main features" |
| Missing error case | Only happy path | Include: "WHEN user provides invalid input THEN system SHALL display specific error message" |

---

## Phase 2: Design

### Purpose
Translate approved requirements into a comprehensive technical blueprint for implementation.

### Process

1. **Analyze Requirements and Plan Research**
   - Review each requirement and its implications
   - Identify technical unknowns needing research
   - Set research boundaries to avoid analysis paralysis

2. **Create System Architecture**
   - System overview and how it fits into broader architecture
   - Component architecture and relationships
   - Data flow through the system
   - Technology stack decisions with rationale

3. **Define Components and Interfaces**
   - Each component's purpose and responsibilities
   - Interfaces between components
   - Dependencies and configuration

4. **Design Data Models**
   - Entity definitions with properties
   - Validation rules and relationships
   - Storage considerations

5. **Plan Error Handling**
   - Error categories and response strategies
   - User-facing error messages
   - Recovery mechanisms

6. **Define Testing Strategy**
   - Unit, integration, and E2E testing approaches
   - Test coverage targets
   - Testing tools and frameworks

### Design Document Structure

```markdown
# Design: [Feature Name]

## Overview
[Summary of approach, linking back to requirements]

### Design Goals
- [Goal 1]
- [Goal 2]

### Key Design Decisions
- [Decision 1]: [Rationale]
- [Decision 2]: [Rationale]

## Architecture

### System Overview
[High-level description of how the system works]

### Component Architecture
[Major components and their relationships - use diagrams if helpful]

### Technology Stack
| Layer | Technology | Rationale |
|-------|------------|-----------|
| [Layer] | [Tech] | [Why chosen] |

## Components and Interfaces

### [Component Name]
- **Purpose**: [What it does]
- **Responsibilities**: [Key duties]
- **Interfaces**: Input/Output/Dependencies
- **Implementation Notes**: [Key details]

## Data Models

### [Entity Name]
```typescript
interface EntityName {
  id: string;
  property1: string;
  // ...
}
```
- **Validation Rules**: [Rules]
- **Relationships**: [Connections to other entities]

## API Design

### [Endpoint Name]
- **Method**: POST/GET/PUT/DELETE
- **Path**: /api/v1/[resource]
- **Request**: [Schema]
- **Response**: [Schema]
- **Errors**: [Error codes and when they occur]

## Error Handling
| Category | HTTP Status | User Action |
|----------|-------------|-------------|
| Validation | 400 | Fix input and retry |
| Authentication | 401 | Re-authenticate |
| Server Error | 500 | Retry later |

## Testing Strategy
- **Unit Testing**: [Approach, coverage target]
- **Integration Testing**: [Approach]
- **E2E Testing**: [Key scenarios]
```

### Design Decision Documentation

For significant decisions, document:

```markdown
### Decision: [Brief title]

**Context**: [Situation requiring a decision]

**Options Considered**:
1. **[Option 1]**
   - Pros: [Benefits]
   - Cons: [Drawbacks]
2. **[Option 2]**
   - Pros: [Benefits]
   - Cons: [Drawbacks]

**Decision**: [Chosen option]
**Rationale**: [Why this option was selected]
```

### Design Quality Checklist

Before proceeding to Tasks:
- [ ] All requirements are addressed in the design
- [ ] Component responsibilities are well-defined
- [ ] Interfaces between components are specified
- [ ] Technology choices are justified
- [ ] Data models are complete with validation rules
- [ ] Error handling covers expected failure modes
- [ ] Testing strategy is comprehensive
- [ ] Design is technically feasible
- [ ] Security considerations are addressed

### Common Pitfalls

| Problem | Solution |
|---------|----------|
| Over-engineering | Focus on current requirements, design for extensibility but don't implement unused features |
| Under-specified interfaces | Clearly define what each component does and how they communicate |
| Ignoring non-functional requirements | Explicitly address performance, security, scalability |
| Technology-first design | Let requirements drive technology choices |
| Only happy path | Design error handling and edge case behavior |

---

## Phase 3: Tasks

### Purpose
Break down the design into sequenced, actionable coding tasks that can be executed incrementally.

### Process

1. **Identify Implementation Tasks**
   - Review design components that need to be built
   - Map to code artifacts (files, classes, functions)
   - Identify dependencies between tasks

2. **Structure Tasks**
   - Use two-level hierarchy maximum (major tasks + sub-tasks)
   - Group related tasks logically
   - Sequence to respect dependencies

3. **Define Each Task**
   - Clear objective (what specific code to write)
   - Implementation details (files, components, functions)
   - Requirements traceability (which requirements it implements)
   - Testing expectations

4. **Validate Task Plan**
   - Each task is actionable without clarification
   - Tasks produce working, testable code
   - Dependencies are respected in sequence
   - All design components are covered

### Task Document Structure

```markdown
# Tasks: [Feature Name]

## Implementation Overview
[Brief summary of implementation strategy]

## Implementation Plan

- [ ] 1. Set up foundation
- [ ] 1.1 Create project structure and core interfaces
  - Set up directory structure for [components]
  - Define TypeScript interfaces for [types]
  - Create base configuration
  - _Requirements: 1.1, 2.1_

- [ ] 1.2 Set up testing framework and database
  - Configure [testing framework]
  - Set up test database
  - Create database migrations
  - _Requirements: 1.1_

- [ ] 2. Implement data layer
- [ ] 2.1 Create [Entity] model with validation
  - Implement [Entity] class with [fields]
  - Add validation methods for [rules]
  - Write unit tests for validation
  - _Requirements: 2.1, 3.1_

- [ ] 3. Create business logic services
- [ ] 3.1 Implement [Service] service
  - Create [Service] with [methods]
  - Add error handling and logging
  - Write unit tests
  - _Requirements: 1.2, 4.1_

- [ ] 4. Create API endpoints
- [ ] 4.1 Implement [Resource] endpoints
  - Create POST/GET/PUT/DELETE endpoints
  - Add request validation and error handling
  - Write integration tests
  - _Requirements: 2.3, 6.1_

- [ ] 5. Integration and testing
- [ ] 5.1 End-to-end integration testing
  - Create complete workflow tests
  - Test error scenarios and edge cases
  - Validate against requirements
  - _Requirements: All_
```

### Task Sequencing Strategies

| Strategy | Best For | Sequence |
|----------|----------|----------|
| **Foundation-First** | New projects, complex systems | Setup → Models → Services → API → Integration |
| **Feature-Slice** | MVPs, user-facing apps | Complete vertical slice of each feature |
| **Risk-First** | High uncertainty projects | Most uncertain/complex components first |
| **Hybrid** | Most real-world projects | Minimal foundation → High-value slice → Expand |

### Task Writing Guidelines

**Good Task:**
```markdown
- [ ] 2.1 Create User model with validation
  - Implement User class with email, password, name, createdAt fields
  - Add validation for email format (RFC 5322) and password strength (8+ chars, mixed case)
  - Write unit tests covering valid/invalid scenarios
  - _Requirements: 1.2, 2.1_
```

**Bad Task:**
```markdown
- [ ] 2.1 Build user stuff
  - Make user things work
```

### Task Quality Checklist

Before beginning implementation:
- [ ] All design components are covered by tasks
- [ ] All requirements are traced to tasks
- [ ] Each task has clear, specific objective
- [ ] Task descriptions specify files/components to create
- [ ] Tasks are ordered to respect dependencies
- [ ] Each task produces testable code
- [ ] Scope is appropriate (1-4 hours of focused work)
- [ ] No non-coding tasks (deploy, get feedback, etc.)

### Common Pitfalls

| Problem | Solution |
|---------|----------|
| Tasks too abstract | Add specific files, functions, components to create |
| Missing dependencies | Sequence tasks so each builds on completed work |
| Monolithic tasks | Break into smaller incremental steps |
| Missing tests | Include test creation in each task |
| Non-coding tasks | Focus only on implementation activities |

---

## Execution Guide

### Before Starting Any Task

1. Read task details thoroughly
2. Review referenced requirements
3. Verify prerequisite tasks are complete
4. Identify success criteria

### During Implementation

1. Mark task as "in progress"
2. Write tests first (when applicable)
3. Implement incrementally
4. Test continuously
5. Document as you go

### Before Marking Complete

1. All tests pass
2. Task delivers required functionality
3. Code integrates with existing components
4. No regressions introduced

### When Tasks Take Longer Than Expected

1. Assess if scope has grown beyond intent
2. Consider splitting into smaller pieces
3. Update estimates for remaining tasks

### When Requirements Change

1. Stop current work
2. Update requirements document first
3. Revise design if needed
4. Update affected tasks
5. Resume with updated context

---

## Quick Reference

### EARS Patterns
- **WHEN** [event] **THEN** system **SHALL** [response]
- **IF** [condition] **THEN** system **SHALL** [behavior]
- **WHILE** [ongoing] system **SHALL** [continuous behavior]
- **WHERE** [context] system **SHALL** [contextual behavior]

### Phase Outputs
| Phase | Output | Key Sections |
|-------|--------|--------------|
| Requirements | Requirements.md | User Stories, Acceptance Criteria (EARS), Non-Functional Requirements |
| Design | Design.md | Architecture, Components, Data Models, API Design, Error Handling, Testing Strategy |
| Tasks | Tasks.md | Sequenced implementation tasks with requirements traceability |

### Approval Gates
- **Requirements → Design**: All requirements testable, complete coverage of scenarios, stakeholder alignment
- **Design → Tasks**: All requirements addressed, technically feasible, interfaces specified
- **Tasks → Implementation**: All design covered, dependencies sequenced, tasks actionable

---

## Example: User Authentication Feature

### Requirements (excerpt)
```markdown
### Requirement 1: User Registration
**User Story:** As a new user, I want to create an account, so that I can access personalized features.

#### Acceptance Criteria
1. WHEN user provides valid email and password THEN system SHALL create new account
2. WHEN user provides existing email THEN system SHALL display "email already registered" error
3. WHEN user provides invalid email format THEN system SHALL display "invalid email format" error
4. WHEN user provides password shorter than 8 characters THEN system SHALL display "password too short" error
5. WHEN account creation succeeds THEN system SHALL send confirmation email
```

### Design (excerpt)
```markdown
## Components

### AuthService
- **Purpose**: Handle user authentication and session management
- **Responsibilities**: Registration, login, password hashing, token generation
- **Interfaces**:
  - Input: UserRegistrationDTO, LoginCredentials
  - Output: AuthResult, JWTToken
  - Dependencies: UserRepository, EmailService

## Data Models

### User
```typescript
interface User {
  id: string;
  email: string;
  passwordHash: string;
  createdAt: Date;
  isVerified: boolean;
}
```
- **Validation**: Email RFC 5322, password min 8 chars
```

### Tasks (excerpt)
```markdown
- [ ] 2. Implement core authentication
- [ ] 2.1 Create User model with validation
  - Implement User class with email, passwordHash, createdAt, isVerified fields
  - Add email format validation (RFC 5322)
  - Add password strength validation (8+ chars)
  - Write unit tests for all validation rules
  - _Requirements: 1.1, 1.3, 1.4_

- [ ] 2.2 Implement AuthService registration
  - Create AuthService with register() method
  - Add bcrypt password hashing
  - Check for existing email before registration
  - Write unit tests for registration logic
  - _Requirements: 1.1, 1.2_
```

---

## When to Use This Methodology

### Ideal For
- Complex features with multiple components
- Features requiring clear stakeholder alignment
- Team collaboration across developers
- AI-assisted development workflows
- Projects where documentation matters

### Less Suitable For
- Simple bug fixes
- Experimental prototypes
- Time-critical hotfixes
- Well-established, repetitive patterns

### Lightweight Alternative

For simpler features, use a condensed approach:
1. Single document with abbreviated Requirements + Design + Tasks
2. Focus on core user stories and main technical approach
3. Fewer but higher-level tasks

---

*Apply this methodology to transform vague feature ideas into systematic, high-quality implementations.*
