### ✅ План: Поддержка множественного выделения и единое удаление

#### 1. **Изменить режим выделения во всех таблицах/деревьях**
   - В `TransferDialog`, `AccountDialog`, `OperationDialog`, `CategoryDialog`:
     ```python
     widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
     widget.setSelectionBehavior(QAbstractItemView.SelectRows)
     ```
   - Применить к:
     - `transfers_tree` (переводы)
     - `accounts_tree` (счета)
     - `operations_table` (транзакции)
     - `categories_tree` (категории)

#### 2. **Добавить универсальный метод `_get_selected_ids()` в `BaseDialog`**
   - Метод должен работать с `QTreeWidget` и `QTableWidget`
   - Использовать `Qt.UserRole` для извлечения ID
   - Возвращать `List[int]`
   - Пример сигнатуры:
     ```python
     def _get_selected_ids(self, widget) -> List[int]:
         """Возвращает список ID выделенных элементов."""
     ```

#### 3. **Обновить контекстное меню и UI-методы удаления**
   - Заменить одиночное удаление на множественное:
     ```python
     selected_ids = self._get_selected_ids(self.transfers_tree)
     if selected_ids:
         self.presenter.delete_transfers(selected_ids)
     ```
   - Убрать прямую работу с БД из UI
   - Не показывать меню для системных записей — проверка через `Qt.UserRole + 1`

#### 4. **Стандартизировать метод удаления в презентерах**
   - Все презентеры (`TransferPresenter`, `AccountPresenter` и т.д.) должны иметь:
     ```python
     def delete_items(self, item_ids: List[int]):
         try:
             for item_id in item_ids:
                 self.service.delete_item(item_id)
             self.view.show_status(f"Удалено: {len(item_ids)}", "success")
             self.view.clear_selection()
             self._load_data()
         except Exception as e:
             self.view.show_status(f"Ошибка: {e}", "error")
     ```
   - После удаления обязательно вызывать метод self.view.clear_selection() для очитки выделения
   - Сирвис и ниже не трогаем только UI и Presenter