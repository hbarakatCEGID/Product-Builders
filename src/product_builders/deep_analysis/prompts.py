"""Adaptive prompt generation for the bootstrap meta-rule template.

Uses heuristic analysis results from Phase 1 to generate tech-stack-specific
questions for Cursor deep analysis (Phase 2). Different tech stacks need
different deep analysis questions -- a Django project needs questions about
app coupling, while a React project needs questions about component boundaries.
"""

from __future__ import annotations

from product_builders.models.profile import ProductProfile

_MAX_QUESTIONS_PER_STEP = 6

_NEXTJS_NAMES = frozenset({"next", "next.js", "nextjs"})
_REACT_NAMES = frozenset({"react", "react.js"})
_SPRING_NAMES = frozenset({"spring", "spring-boot", "spring boot"})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _detect_framework(profile: ProductProfile) -> str | None:
    """Return the primary framework name (lowercased) or *None*."""
    for fw in profile.tech_stack.frameworks:
        if fw.name:
            return fw.name.lower()
    return None


def _is_language(profile: ProductProfile, lang: str) -> bool:
    """Check whether *lang* is the primary language (case-insensitive)."""
    if profile.tech_stack.primary_language:
        return profile.tech_stack.primary_language.lower() == lang.lower()
    return False


# ---------------------------------------------------------------------------
# Architecture questions
# ---------------------------------------------------------------------------

_ARCHITECTURE_BASELINE: list[str] = [
    "What is the top-level layering pattern (e.g. layered, hexagonal, feature-based)?",
    "What is the primary dependency direction between modules?",
    "Are there identifiable bounded contexts or major subsystems?",
    "Map cross-module dependencies -- which modules import from which?",
]

_ARCHITECTURE_DJANGO: list[str] = [
    "Are Django apps loosely coupled or do they import from each other?",
    "Is there a service layer, or does logic live in views/serializers?",
    "Map cross-app dependencies",
]

_ARCHITECTURE_FASTAPI: list[str] = [
    "How are routers organized -- feature-based or resource-based?",
    "Is there a domain layer separate from the API layer?",
]

_ARCHITECTURE_NEXTJS: list[str] = [
    "Are you using App Router or Pages Router pattern?",
    "Where does business logic live -- route handlers, lib/, or a service layer?",
    "Is there server/client component separation?",
]

_ARCHITECTURE_REACT_GENERIC: list[str] = [
    "Component tree boundaries vs feature module boundaries?",
    "State colocation patterns?",
]

_ARCHITECTURE_SPRING: list[str] = [
    "Is this layered (Controller->Service->Repository) or hexagonal?",
    "How are bounded contexts mapped to packages?",
]

_ARCHITECTURE_MONOREPO: list[str] = [
    "How do packages/apps depend on each other?",
    "Is there a shared library layer?",
]


def _build_architecture_questions(profile: ProductProfile) -> list[str]:
    """Return architecture questions tailored to the detected tech stack."""
    framework = _detect_framework(profile)
    is_python = _is_language(profile, "python")
    is_typescript = _is_language(profile, "typescript")
    is_java = _is_language(profile, "java")

    questions: list[str] = list(_ARCHITECTURE_BASELINE)

    # Tech-specific additions
    if is_python and framework == "django":
        questions.extend(_ARCHITECTURE_DJANGO)
    elif is_python and framework == "fastapi":
        questions.extend(_ARCHITECTURE_FASTAPI)
    elif is_typescript and framework in _NEXTJS_NAMES:
        questions.extend(_ARCHITECTURE_NEXTJS)
    elif is_typescript and framework in _REACT_NAMES:
        questions.extend(_ARCHITECTURE_REACT_GENERIC)
    elif is_java and framework in _SPRING_NAMES:
        questions.extend(_ARCHITECTURE_SPRING)

    if profile.structure.is_monorepo:
        questions.extend(_ARCHITECTURE_MONOREPO)

    return questions[:_MAX_QUESTIONS_PER_STEP]


# ---------------------------------------------------------------------------
# Domain model questions
# ---------------------------------------------------------------------------

_DOMAIN_MODEL_BASELINE: list[str] = [
    "Where do domain rules live?",
    "Identify value objects vs entities",
]


def _build_domain_model_questions(profile: ProductProfile) -> list[str]:
    """Return domain-model questions adapted to the project's data layer."""
    questions: list[str] = list(_DOMAIN_MODEL_BASELINE)

    # ORM-specific
    orm = profile.database.orm
    if orm:
        questions.append(
            f"Examine {orm} models/entities for domain vocabulary"
        )
        questions.append(
            "Map entity relationships from schema definitions"
        )

    # API-style-specific
    api_style = (profile.api.api_style or "").lower()
    if api_style == "graphql":
        questions.append("How do resolvers map to domain concepts?")
        questions.append("Schema-first or code-first approach?")
    elif api_style == "rest":
        questions.append(
            "Do API resources map 1:1 to domain entities or are there aggregation endpoints?"
        )

    # Ensure a minimum useful count
    if len(questions) < 4:
        questions.append(
            "What naming patterns appear in model/entity definitions?"
        )
        questions.append(
            "Are there explicit domain events, commands, or query objects?"
        )

    return questions[:_MAX_QUESTIONS_PER_STEP]


# ---------------------------------------------------------------------------
# Conventions questions
# ---------------------------------------------------------------------------

_CONVENTIONS_BASELINE: list[str] = [
    "Naming philosophy -- verbose or terse?",
    "Abstraction level -- thin controllers + fat services?",
]


def _build_conventions_questions(profile: ProductProfile) -> list[str]:
    """Return conventions questions based on detected tooling."""
    questions: list[str] = list(_CONVENTIONS_BASELINE)

    linter = profile.conventions.linter
    formatter = profile.conventions.formatter

    if linter or formatter:
        tool_names = "/".join(filter(None, [linter, formatter]))
        questions.append(
            f"Beyond {tool_names}, what naming patterns are consistently followed?"
        )

    test_framework = profile.testing.test_framework
    if test_framework:
        questions.append("What's the test file organization pattern?")
        questions.append("Test naming conventions?")

    # Ensure a minimum useful count
    if len(questions) < 4:
        questions.append(
            "How are imports organized -- grouped by type, alphabetical, or ad hoc?"
        )
        questions.append(
            "Are there consistent patterns for error messages and log formatting?"
        )

    return questions[:_MAX_QUESTIONS_PER_STEP]


# ---------------------------------------------------------------------------
# Public API: build_adaptive_questions
# ---------------------------------------------------------------------------


def build_gap_aware_questions(
    profile: ProductProfile,
) -> dict[str, list[str]]:
    """Return questions that target what heuristic analysis COULDN'T determine.

    Unlike adaptive questions (which vary by framework), gap-aware questions
    reference what WAS detected and ask about what's MISSING — filling
    specific holes in the profile rather than asking generic questions.
    """
    architecture: list[str] = []
    database: list[str] = []
    auth: list[str] = []
    conventions: list[str] = []

    framework = _detect_framework(profile)
    lang = (profile.tech_stack.primary_language or "").lower()
    src_dirs = ", ".join(profile.structure.source_directories) if profile.structure.source_directories else "the source directory"

    # --- Architecture gaps ---
    if not profile.architecture_deep.layering_pattern:
        if framework:
            architecture.append(
                f"We detected {framework} but couldn't determine the architecture pattern. "
                f"Is the project layered (route handlers → services → data access), "
                f"feature-based, or something else? Check {src_dirs}."
            )
        else:
            architecture.append(
                "What architecture pattern does this project follow? "
                "(layered, hexagonal, feature-based, flat?) "
                f"Examine the directory structure under {src_dirs}."
            )

    if not profile.architecture_deep.bounded_contexts:
        key_dirs = [d.path for d in profile.structure.key_directories[:5]]
        if key_dirs:
            architecture.append(
                f"These directories were detected: {', '.join(key_dirs)}. "
                "Are they bounded contexts / domain modules, or just structural grouping? "
                "Which ones depend on each other?"
            )

    if not profile.architecture_deep.dependency_direction:
        architecture.append(
            "What is the dependency direction? Do outer layers depend on inner layers, "
            "or is it ad-hoc? Check import statements across modules."
        )

    # --- Database gaps ---
    if profile.database.database_type and not profile.database.orm:
        db = profile.database.database_type
        architecture_hint = ""
        if profile.auth.auth_strategy and profile.auth.auth_strategy.lower() == "supabase":
            architecture_hint = " (Supabase detected — check for Supabase client usage)"
        database.append(
            f"We detected {db} but no ORM. How does the project query the database? "
            f"Direct client library? Query builder? Raw SQL?{architecture_hint}"
        )

    if profile.database.migration_directory:
        if not profile.database.migration_tool:
            database.append(
                f"Migrations found at `{profile.database.migration_directory}` "
                "but the migration tool couldn't be identified. "
                "What tool generates and runs these migrations?"
            )
    elif profile.database.database_type and not profile.database.migration_directory:
        database.append(
            f"Database ({profile.database.database_type}) detected but no migration "
            "directory found. Are migrations managed externally (e.g., Supabase dashboard, "
            "hosted service) or is there an undiscovered migration directory?"
        )

    if not profile.database.schema_naming_convention and profile.database.database_type:
        database.append(
            "What naming convention is used for tables and columns? "
            "(snake_case, camelCase, PascalCase?)"
        )

    if not profile.database.relationship_patterns and profile.database.database_type:
        database.append(
            "What entity relationships exist? Check schema definitions "
            "or model files for foreign keys, join tables, and associations."
        )

    # --- Auth gaps ---
    if profile.auth.auth_strategy and not profile.auth.auth_middleware:
        api_dirs = ", ".join(profile.api.api_directories) if profile.api.api_directories else "the API directory"
        auth.append(
            f"Auth strategy detected as {profile.auth.auth_strategy}, but no auth "
            f"middleware was found. How do API routes at {api_dirs} validate "
            "authentication? Is it middleware, per-route checks, or RLS?"
        )

    if profile.auth.auth_strategy and not profile.auth.protected_route_patterns:
        auth.append(
            "No protected route patterns detected. Which routes require "
            "authentication? What does the protection pattern look like?"
        )

    if profile.auth.auth_strategy and not profile.auth.auth_directories:
        auth.append(
            "Where does auth-related code live? (auth utils, guards, "
            "middleware, session management)"
        )

    if profile.auth.auth_strategy and not profile.auth.oauth_providers and not profile.auth.mfa_methods:
        auth.append(
            f"Auth is {profile.auth.auth_strategy}. Are there OAuth providers "
            "configured? Any MFA/2FA methods enabled?"
        )

    # --- Conventions gaps ---
    if not profile.conventions.naming_convention and not profile.implicit_conventions_deep.naming_philosophy:
        conventions.append(
            "What naming convention is followed? "
            "(camelCase, snake_case, PascalCase for variables/functions/classes?) "
            "Check 5+ files for consistent patterns."
        )

    if not profile.conventions.import_ordering:
        linter = profile.conventions.linter
        if linter:
            conventions.append(
                f"Linter ({linter}) is configured but import ordering couldn't be "
                "determined. Are imports grouped by type (stdlib → external → local)?"
            )

    if not profile.error_handling.logging_framework and not profile.error_handling.logging_frameworks:
        conventions.append(
            "No logging framework detected. How does this project log? "
            "Console.log, a logger library, or a custom solution?"
        )

    if not profile.error_handling.error_response_format and profile.api.api_style:
        conventions.append(
            "What format do API error responses follow? "
            "Is there a standard error envelope (e.g., {error: {code, message}})?"
        )

    if (
        not profile.state_management.data_fetching_library
        and not profile.state_management.data_fetching_libraries
        and lang in ("typescript", "javascript")
    ):
        conventions.append(
            "No data fetching library detected (React Query, SWR, etc.). "
            "How does this project fetch data from API routes? "
            "Custom hooks, fetch() calls, or another pattern?"
        )

    return {
        "architecture": architecture[:_MAX_QUESTIONS_PER_STEP],
        "database": database[:_MAX_QUESTIONS_PER_STEP],
        "auth": auth[:_MAX_QUESTIONS_PER_STEP],
        "conventions": conventions[:_MAX_QUESTIONS_PER_STEP],
    }


def build_adaptive_questions(
    profile: ProductProfile,
) -> dict[str, list[str]]:
    """Return tech-stack-specific deep analysis questions organized by step.

    The returned dict has three keys -- ``architecture``, ``domain_model``,
    and ``conventions`` -- each mapping to a list of 4-6 focused questions
    derived from the heuristic analysis in *profile*.
    """
    return {
        "architecture": _build_architecture_questions(profile),
        "domain_model": _build_domain_model_questions(profile),
        "conventions": _build_conventions_questions(profile),
    }


# ---------------------------------------------------------------------------
# YAML example helpers
# ---------------------------------------------------------------------------

_YAML_PYTHON_DJANGO = """\
architecture_deep:
  layering_pattern: "Layered (Views -> Services -> Models)"
  layering_evidence: "app/services/ contains business logic separate from app/views/"
  dependency_direction: "views -> services -> models (top-down)"
  dependency_evidence: "app/views/orders.py imports from app/services/order_service.py"
  bounded_contexts:
    - name: "Orders"
      evidence: "app/orders/ Django app with own models, views, and serializers"
    - name: "Users"
      evidence: "app/users/ handles authentication, registration, and profiles"
  module_boundaries:
    app/orders:
      depends_on: ["app/users", "app/products"]
      evidence: "app/orders/services.py imports UserService and ProductService"
    app/users:
      depends_on: []
      evidence: "app/users/ has no cross-app imports"

domain_model_deep:
  domain_vocabulary:
    - term: "Order"
      evidence: "app/orders/models.py:Order"
    - term: "LineItem"
      evidence: "app/orders/models.py:LineItem"
  entity_relationships:
    - from: "Order"
      to: "User"
      type: "many-to-one"
      evidence: "app/orders/models.py:Order.customer ForeignKey"
    - from: "Order"
      to: "LineItem"
      type: "one-to-many"
      evidence: "app/orders/models.py:LineItem.order ForeignKey"
  business_logic_locations:
    - path: "app/services/"
      description: "Service layer containing order processing, pricing, and notifications"
      evidence: "app/services/order_service.py"

implicit_conventions_deep:
  naming_philosophy: "Verbose, intention-revealing names following Django conventions"
  naming_evidence: "get_active_orders_for_user(), OrderCreateSerializer"
  abstraction_level: "Fat services, thin views -- views delegate to service functions"
  abstraction_evidence: "app/views/orders.py calls OrderService methods, no inline logic"
  code_organization_habits:
    - pattern: "One Django app per bounded context"
      evidence: "app/orders/, app/users/, app/products/ each have models, views, serializers"
    - pattern: "Shared utilities in app/core/"
      evidence: "app/core/permissions.py, app/core/pagination.py"
  error_handling_philosophy: "DRF exception handler with custom error codes"
  error_evidence: "app/core/exceptions.py defines BusinessLogicError base class"
"""

_YAML_TYPESCRIPT_REACT = """\
architecture_deep:
  layering_pattern: "Feature-based modules with shared hooks"
  layering_evidence: "src/features/ contains isolated feature folders"
  dependency_direction: "features -> shared -> lib (inward)"
  dependency_evidence: "src/features/orders/hooks.ts imports from src/shared/api-client.ts"
  bounded_contexts:
    - name: "Orders"
      evidence: "src/features/orders/ with own components, hooks, and types"
    - name: "Dashboard"
      evidence: "src/features/dashboard/ aggregates data from multiple domains"
  module_boundaries:
    src/features/orders:
      depends_on: ["src/shared", "src/lib"]
      evidence: "src/features/orders/hooks.ts imports from src/shared/api-client.ts"
    src/features/dashboard:
      depends_on: ["src/features/orders", "src/shared"]
      evidence: "src/features/dashboard/components/OrderSummary.tsx imports useOrders hook"

domain_model_deep:
  domain_vocabulary:
    - term: "Order"
      evidence: "src/features/orders/types.ts:Order interface"
    - term: "CartItem"
      evidence: "src/features/cart/types.ts:CartItem interface"
  entity_relationships:
    - from: "Order"
      to: "User"
      type: "many-to-one"
      evidence: "src/features/orders/types.ts:Order.userId"
    - from: "Order"
      to: "CartItem"
      type: "one-to-many"
      evidence: "src/features/orders/types.ts:Order.items: CartItem[]"
  business_logic_locations:
    - path: "src/features/orders/hooks/"
      description: "Order CRUD operations and state management via React Query"
      evidence: "src/features/orders/hooks/useCreateOrder.ts"

implicit_conventions_deep:
  naming_philosophy: "PascalCase components, camelCase hooks prefixed with 'use'"
  naming_evidence: "OrderList.tsx, useOrders.ts, useCreateOrder.ts"
  abstraction_level: "Thin route components, logic in custom hooks"
  abstraction_evidence: "src/features/orders/pages/OrdersPage.tsx delegates to useOrders hook"
  code_organization_habits:
    - pattern: "Feature folders with collocated components, hooks, types, and tests"
      evidence: "src/features/orders/{components,hooks,types.ts,__tests__}"
    - pattern: "Barrel exports via index.ts in each feature"
      evidence: "src/features/orders/index.ts re-exports public API"
  error_handling_philosophy: "Error boundaries at feature level with toast notifications"
  error_evidence: "src/shared/components/ErrorBoundary.tsx wraps each feature route"
"""

_YAML_JAVA_SPRING = """\
architecture_deep:
  layering_pattern: "Layered (Controller -> Service -> Repository)"
  layering_evidence: "src/main/java/com/example/app/ has controller/, service/, repository/ packages"
  dependency_direction: "controller -> service -> repository (top-down)"
  dependency_evidence: "OrderController injects OrderService; OrderService injects OrderRepository"
  bounded_contexts:
    - name: "Order"
      evidence: "com.example.app.order package with full vertical slice"
    - name: "User"
      evidence: "com.example.app.user package with controller, service, repository"
  module_boundaries:
    com.example.app.order:
      depends_on: ["com.example.app.user", "com.example.app.common"]
      evidence: "OrderService.java imports UserService"
    com.example.app.user:
      depends_on: ["com.example.app.common"]
      evidence: "UserService.java only imports from common"

domain_model_deep:
  domain_vocabulary:
    - term: "Order"
      evidence: "com.example.app.order.entity.Order JPA entity"
    - term: "OrderItem"
      evidence: "com.example.app.order.entity.OrderItem JPA entity"
  entity_relationships:
    - from: "Order"
      to: "User"
      type: "many-to-one"
      evidence: "Order.java @ManyToOne User customer"
    - from: "Order"
      to: "OrderItem"
      type: "one-to-many"
      evidence: "Order.java @OneToMany List<OrderItem> items"
  business_logic_locations:
    - path: "src/main/java/com/example/app/order/service/"
      description: "Order processing, validation, and pricing logic"
      evidence: "OrderService.java"

implicit_conventions_deep:
  naming_philosophy: "Standard Java/Spring naming -- PascalCase classes, camelCase methods"
  naming_evidence: "OrderService.createOrder(), OrderRepository.findByStatus()"
  abstraction_level: "Thin controllers, fat services with transactional boundaries"
  abstraction_evidence: "OrderController.java delegates all logic to OrderService"
  code_organization_habits:
    - pattern: "Package-by-feature with layered sub-packages"
      evidence: "com.example.app.order.{controller,service,repository,entity}"
    - pattern: "DTOs separate from entities"
      evidence: "com.example.app.order.dto.OrderRequest, OrderResponse"
  error_handling_philosophy: "@ControllerAdvice global exception handler with RFC 7807 problem details"
  error_evidence: "com.example.app.common.exception.GlobalExceptionHandler.java"
"""

_YAML_GENERIC = """\
architecture_deep:
  layering_pattern: "<pattern name -- e.g. Layered, Hexagonal, Feature-based>"
  layering_evidence: "<file path demonstrating the pattern>"
  dependency_direction: "<direction -- e.g. inward, top-down>"
  dependency_evidence: "<file path showing import direction>"
  bounded_contexts:
    - name: "<context name>"
      evidence: "<file path or directory>"
  module_boundaries:
    <module_path>:
      depends_on: ["<other_module>"]
      evidence: "<file showing dependency>"

domain_model_deep:
  domain_vocabulary:
    - term: "<DomainTerm>"
      evidence: "<file path:ClassName or definition>"
  entity_relationships:
    - from: "<EntityA>"
      to: "<EntityB>"
      type: "<relationship type -- e.g. one-to-many, many-to-one>"
      evidence: "<file path showing relationship>"
  business_logic_locations:
    - path: "<directory path>"
      description: "<what business logic lives here>"
      evidence: "<key file>"

implicit_conventions_deep:
  naming_philosophy: "<description of naming style>"
  naming_evidence: "<file path or example names>"
  abstraction_level: "<description of where logic lives>"
  abstraction_evidence: "<file path or example>"
  code_organization_habits:
    - pattern: "<recurring organizational pattern>"
      evidence: "<file path>"
  error_handling_philosophy: "<description of error handling approach>"
  error_evidence: "<file path>"
"""


def _select_yaml_example(profile: ProductProfile) -> str:
    """Pick the most relevant YAML example based on primary language."""
    _LANG_EXAMPLES: dict[str, str] = {
        "python": _YAML_PYTHON_DJANGO,
        "typescript": _YAML_TYPESCRIPT_REACT,
        "javascript": _YAML_TYPESCRIPT_REACT,
        "java": _YAML_JAVA_SPRING,
    }

    lang = (profile.tech_stack.primary_language or "").lower()
    return _LANG_EXAMPLES.get(lang, _YAML_GENERIC)


# ---------------------------------------------------------------------------
# Public API: get_output_yaml_example
# ---------------------------------------------------------------------------


def get_output_yaml_example(profile: ProductProfile) -> str:
    """Return a complete, filled-in YAML example for deep-analysis.yaml.

    The example uses tech-relevant values based on the detected tech stack
    so that users have a concrete reference for the expected output format.
    For unknown or unsupported stacks, a generic placeholder template is
    returned.
    """
    return _select_yaml_example(profile).strip()
