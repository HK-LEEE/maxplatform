#!/bin/bash
# Auto-generated cleanup script for removing print() statements
# Review each change before applying!

echo "🧹 Cleaning up print() statements from test and init scripts..."


# Clean ./init_permission_system.py (28 prints)
echo "Cleaning ./init_permission_system.py..."
sed -i '/^[[:space:]]*print(/d' "./init_permission_system.py"

# Clean ./run_migration.py (10 prints)
echo "Cleaning ./run_migration.py..."
sed -i '/^[[:space:]]*print(/d' "./run_migration.py"

# Clean ./create_tables_fixed.py (9 prints)
echo "Cleaning ./create_tables_fixed.py..."
sed -i '/^[[:space:]]*print(/d' "./create_tables_fixed.py"

# Clean ./add_features_via_api.py (36 prints)
echo "Cleaning ./add_features_via_api.py..."
sed -i '/^[[:space:]]*print(/d' "./add_features_via_api.py"

# Clean ./init_service_system.py (29 prints)
echo "Cleaning ./init_service_system.py..."
sed -i '/^[[:space:]]*print(/d' "./init_service_system.py"

# Clean ./create_roles.py (7 prints)
echo "Cleaning ./create_roles.py..."
sed -i '/^[[:space:]]*print(/d' "./create_roles.py"

# Clean ./test_workspace_api.py (11 prints)
echo "Cleaning ./test_workspace_api.py..."
sed -i '/^[[:space:]]*print(/d' "./test_workspace_api.py"

# Clean ./update_oauth_clients.py (12 prints)
echo "Cleaning ./update_oauth_clients.py..."
sed -i '/^[[:space:]]*print(/d' "./update_oauth_clients.py"

# Clean ./init_mssql.py (47 prints)
echo "Cleaning ./init_mssql.py..."
sed -i '/^[[:space:]]*print(/d' "./init_mssql.py"

# Clean ./create_admin_user.py (13 prints)
echo "Cleaning ./create_admin_user.py..."
sed -i '/^[[:space:]]*print(/d' "./create_admin_user.py"

# Clean ./restore_features_data.py (22 prints)
echo "Cleaning ./restore_features_data.py..."
sed -i '/^[[:space:]]*print(/d' "./restore_features_data.py"

# Clean ./run_migration_simple.py (28 prints)
echo "Cleaning ./run_migration_simple.py..."
sed -i '/^[[:space:]]*print(/d' "./run_migration_simple.py"

# Clean ./setup_platform.py (39 prints)
echo "Cleaning ./setup_platform.py..."
sed -i '/^[[:space:]]*print(/d' "./setup_platform.py"

# Clean ./fix_jupyter_kernel.py (30 prints)
echo "Cleaning ./fix_jupyter_kernel.py..."
sed -i '/^[[:space:]]*print(/d' "./fix_jupyter_kernel.py"

# Clean ./migrate_user_table.py (21 prints)
echo "Cleaning ./migrate_user_table.py..."
sed -i '/^[[:space:]]*print(/d' "./migrate_user_table.py"

# Clean ./add_default_features.py (13 prints)
echo "Cleaning ./add_default_features.py..."
sed -i '/^[[:space:]]*print(/d' "./add_default_features.py"

# Clean ./test_mssql_connection.py (52 prints)
echo "Cleaning ./test_mssql_connection.py..."
sed -i '/^[[:space:]]*print(/d' "./test_mssql_connection.py"

# Clean ./monitor_refresh_tokens.py (11 prints)
echo "Cleaning ./monitor_refresh_tokens.py..."
sed -i '/^[[:space:]]*print(/d' "./monitor_refresh_tokens.py"

# Clean ./init_db.py (12 prints)
echo "Cleaning ./init_db.py..."
sed -i '/^[[:space:]]*print(/d' "./init_db.py"

# Clean ./add_columns.py (8 prints)
echo "Cleaning ./add_columns.py..."
sed -i '/^[[:space:]]*print(/d' "./add_columns.py"

# Clean ./test_login.py (11 prints)
echo "Cleaning ./test_login.py..."
sed -i '/^[[:space:]]*print(/d' "./test_login.py"

# Clean ./test_login_debug.py (15 prints)
echo "Cleaning ./test_login_debug.py..."
sed -i '/^[[:space:]]*print(/d' "./test_login_debug.py"

# Clean ./debug_token_hash.py (44 prints)
echo "Cleaning ./debug_token_hash.py..."
sed -i '/^[[:space:]]*print(/d' "./debug_token_hash.py"

# Clean ./simulate_refresh_flow.py (36 prints)
echo "Cleaning ./simulate_refresh_flow.py..."
sed -i '/^[[:space:]]*print(/d' "./simulate_refresh_flow.py"

# Clean ./test_refresh_token_fix.py (18 prints)
echo "Cleaning ./test_refresh_token_fix.py..."
sed -i '/^[[:space:]]*print(/d' "./test_refresh_token_fix.py"

# Clean ./generate_passwords.py (8 prints)
echo "Cleaning ./generate_passwords.py..."
sed -i '/^[[:space:]]*print(/d' "./generate_passwords.py"

# Clean ./init_service_system_local.py (23 prints)
echo "Cleaning ./init_service_system_local.py..."
sed -i '/^[[:space:]]*print(/d' "./init_service_system_local.py"

# Clean ./create_oauth_schema_v2.py (24 prints)
echo "Cleaning ./create_oauth_schema_v2.py..."
sed -i '/^[[:space:]]*print(/d' "./create_oauth_schema_v2.py"

# Clean ./create_oauth_schema.py (15 prints)
echo "Cleaning ./create_oauth_schema.py..."
sed -i '/^[[:space:]]*print(/d' "./create_oauth_schema.py"

# Clean ./test_password_reset.py (25 prints)
echo "Cleaning ./test_password_reset.py..."
sed -i '/^[[:space:]]*print(/d' "./test_password_reset.py"

# Clean ./test_workspace_simple.py (11 prints)
echo "Cleaning ./test_workspace_simple.py..."
sed -i '/^[[:space:]]*print(/d' "./test_workspace_simple.py"

# Clean ./fix_database_schema.py (16 prints)
echo "Cleaning ./fix_database_schema.py..."
sed -i '/^[[:space:]]*print(/d' "./fix_database_schema.py"

# Clean ./create_tables_only.py (9 prints)
echo "Cleaning ./create_tables_only.py..."
sed -i '/^[[:space:]]*print(/d' "./create_tables_only.py"

# Clean ./test_refresh_token.py (17 prints)
echo "Cleaning ./test_refresh_token.py..."
sed -i '/^[[:space:]]*print(/d' "./test_refresh_token.py"

# Clean ./test_api.py (15 prints)
echo "Cleaning ./test_api.py..."
sed -i '/^[[:space:]]*print(/d' "./test_api.py"

# Clean ./update_workspace_service.py (6 prints)
echo "Cleaning ./update_workspace_service.py..."
sed -i '/^[[:space:]]*print(/d' "./update_workspace_service.py"

# Clean ./debug_auth.py (33 prints)
echo "Cleaning ./debug_auth.py..."
sed -i '/^[[:space:]]*print(/d' "./debug_auth.py"

# Clean ./test_features_api.py (26 prints)
echo "Cleaning ./test_features_api.py..."
sed -i '/^[[:space:]]*print(/d' "./test_features_api.py"

# Clean ./test_graceful_rotation.py (46 prints)
echo "Cleaning ./test_graceful_rotation.py..."
sed -i '/^[[:space:]]*print(/d' "./test_graceful_rotation.py"

# Clean ./test_profile_api.py (27 prints)
echo "Cleaning ./test_profile_api.py..."
sed -i '/^[[:space:]]*print(/d' "./test_profile_api.py"

# Clean ./migrations/migrate_model_permissions.py (35 prints)
echo "Cleaning ./migrations/migrate_model_permissions.py..."
sed -i '/^[[:space:]]*print(/d' "./migrations/migrate_model_permissions.py"

# Clean ./app/init_data.py (42 prints)
echo "Cleaning ./app/init_data.py..."
sed -i '/^[[:space:]]*print(/d' "./app/init_data.py"

echo "✅ Cleanup completed. Please review changes before committing."
