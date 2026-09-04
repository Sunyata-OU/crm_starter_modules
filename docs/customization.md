# Customization & Module Selection

This guide explains how to enable, disable, customize, or physically remove modules from your deployment.

## 🛠️ Environment-based Module Selection

You can select active modules dynamically at runtime using the `CRM_MODULES` environment variable.

```bash
# Enable only Companies and Todo Actions with Kanban
CRM_MODULES=crm_companies,todo_actions uv run crm dev
```

### Why optional modules stay clean:
Unenabled optional modules do **not** register database tables, menu items, or views.

---

## ✂️ Deleting Unwanted Modules

If your project only needs a subset of these modules and you want to remove code permanently:

1. **Delete module directory**:
   ```bash
   rm -rf starter_module/sales_deals
   ```

2. **Remove entry point in `pyproject.toml`**:
   ```toml
   [project.entry-points."crm.modules"]
   db_postgres = "starter_module.db_postgres"
   crm_companies = "starter_module.crm_companies"
   crm_people = "starter_module.crm_people"
   todo_actions = "starter_module.todo_actions"
   # sales_deals entry deleted
   ```

3. **Reinstall in editable mode**:
   ```bash
   uv pip install -e .
   ```

---

## 🎨 Extending Existing Modules

You can add fields or actions to resources defined in `starter-module` from another module without modifying the source:

```python
def register(registry: Registry) -> None:
    # Extend companies resource from another module
    if registry.has_resource("companies"):
        companies = registry.resource("companies")
        companies.add_field(TextField("tax_id", label="Tax ID / VAT"))
```
