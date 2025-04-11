const $ = django.jQuery;
	
document.addEventListener("DOMContentLoaded", function () {
	const options = {
		prefix: "orderdishes",
		emptyCssClass: "empty-form",
		formCssClass: "dynamic-orderdishes",
		deleteCssClass: "inline-deletelink",
		added: null,
		removed: null
	};

	const totalForms = $("#id_" + options.prefix + "-TOTAL_FORMS").prop("autocomplete", "off");
	let nextIndex = parseInt(totalForms.val(), 10);
	const maxForms = $("#id_" + options.prefix + "-MAX_NUM_FORMS").prop("autocomplete", "off");
	const minForms = $("#id_" + options.prefix + "-MIN_NUM_FORMS").prop("autocomplete", "off");
	let selectedDishes = {};
	
	 const updateElementIndex = function(el, prefix, ndx) {
		const id_regex = new RegExp("(" + prefix + "-(\\d+|__prefix__))");
		const replacement = prefix + "-" + ndx;
		if ($(el).prop("for")) {
			$(el).prop("for", $(el).prop("for").replace(id_regex, replacement));
		}
		if (el.id) {
			el.id = el.id.replace(id_regex, replacement);
		}
		if (el.name) {
			el.name = el.name.replace(id_regex, replacement);
		}
	};
	
	function removeEmptySelectedRows() {
		document.querySelectorAll("table tbody tr.dynamic-orderdishes").forEach(row => {
			let select = row.querySelector("td.field-dish select");
			if (select && select.value === "") {
				row.remove();
				$(totalForms).val(parseInt(totalForms.val(), 10) - 1);
			}
		});
	}

		
    function replaceButton() {
		removeEmptySelectedRows();
		
		const addRowRow = document.querySelector("tr.add-row");
        if (addRowRow) {
            addRowRow.remove();
        }
		
        if (document.querySelector(".custom-add-button")) {
            return;
        }

        const table = document.querySelector("fieldset.module > table");
        if (table) {
            const addButton = document.createElement("button");
            addButton.className = "custom-add-button";
            addButton.textContent = "Добавить блюда";

            addButton.addEventListener("click", function (event) {
                event.preventDefault();
                openModal();
            });

            table.parentNode.insertBefore(addButton, table.nextSibling);
        }
    }

    function ensureModalExists() {
        if (!document.querySelector(".product-modal")) {
            const modal = document.createElement("div");
            modal.className = "product-modal";
            modal.innerHTML = `
                <div class="modal-header">
                    <h1>Выберите блюда</h1>
                    <button class="close-button" onclick="closeModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <div id="categories-list" class="categories-list"></div>
                    <div id="dishes-list" class="dishes-list"></div>
                </div>
                <div class="modal-footer">
                    <div id="total-price" class="total-price">Итого: 0</div>
                    <button class="add-button" onclick="addSelectedDishes()">Добавить</button>
                </div>
            `;
            document.body.appendChild(modal);
        }

        if (!document.querySelector(".modal-backdrop")) {
            const backdrop = document.createElement("div");
            backdrop.className = "modal-backdrop";
            backdrop.style.display = "none";
            backdrop.addEventListener("click", closeModal);
            document.body.appendChild(backdrop);
        }
    }

    window.openModal = function () {
        ensureModalExists();
        document.querySelector(".modal-backdrop").style.display = "block";
		document.querySelector(".product-modal").style.display = "flex";
		selectedDishes = {};
        loadCategories();
    };

    window.closeModal = function () {
        document.querySelector(".modal-backdrop").style.display = "none";
        document.querySelector(".product-modal").style.display = "none";
    };

    // Получение данных из JSON
    const categoriesElement = document.getElementById("categories-data");
    const categories = categoriesElement ? JSON.parse(categoriesElement.textContent) : {};

    const dishesElement = document.getElementById("dishes-data");
    const dishes = dishesElement ? JSON.parse(dishesElement.textContent) : {};
    
    function loadCategories() {
        const categoriesList = document.getElementById("categories-list");
        categoriesList.innerHTML = "";

        Object.keys(categories).forEach((categoryId) => {
            const category = categories[categoryId];
            const categoryItem = document.createElement("div");
            categoryItem.className = "category-item";
            categoryItem.textContent = category.Name;
            categoryItem.addEventListener("click", (e) => categorySelected(e, category));
            categoriesList.appendChild(categoryItem);
        });

        if (Object.keys(categories).length > 0) {
            loadDishes(categories[Object.keys(categories)[0]].Dishes);
        }
    }

	function categorySelected(e, category) {
		const listElement = e.target.parentElement;
		if (!!listElement) {
			let siblings = listElement.children;
			Array.from(siblings).forEach(sibling => sibling.classList.remove("select-category"));
			e.target.classList.add("select-category");
		}		
		
		loadDishes(category.Dishes);
	}
	
	function getDishPrice(dishInfo, source) {
        if (['P1-1', 'P1-2'].includes(source)) {
            return dishInfo.Price[1]; // Цена P1
        }
        if (['P2-1', 'P2-2'].includes(source)) {
            return dishInfo.Price[2]; // Цена P2
        }
        return dishInfo.Price[0]; // Обычная цена
    }

    function loadDishes(dishIds) {		
		const source = document.getElementById('id_order_type').value;
        const dishesList = document.getElementById("dishes-list");
        dishesList.innerHTML = "";

        dishIds.forEach((dishId) => {
            if (!dishes[dishId]) return;

            const dish = dishes[dishId];
            const price = dish.Price.length > 0 ? getDishPrice(dish, source) : 0;

            const dishItem = document.createElement("div");
            dishItem.className = "dish-item";
            dishItem.innerHTML = `
                <span class="dishName" data-id="${dishId}">${dish.Name}</span>
                <span class="price">${price}</span>
                <div class="quantity-control">
                    <button class="decrease" data-id="${dishId}">-</button>
                    <span class="quantity" data-id="${dishId}">${selectedDishes[dishId] || 0}</span>
                    <button class="increase" data-id="${dishId}">+</button>
                </div>
            `;
            dishesList.appendChild(dishItem);
        });

        dishesList.removeEventListener("click", updateQuantityHandler);
        dishesList.addEventListener("click", updateQuantityHandler);
    }

    function updateQuantityHandler(e) {
        const dishId = e.target.dataset.id;
        if (!dishId) return;

		const parentEl = e.target.closest(".dish-item");
		const classList = e.target.classList;
        if (classList.contains("increase") || classList.contains("dishName")) {
            selectedDishes[dishId] = (selectedDishes[dishId] || 0) + 1;
			if (parentEl != null && selectedDishes[dishId] > 0)
			{
				parentEl.classList.add("select-dish");
			}
        } else if (classList.contains("decrease") && selectedDishes[dishId] > 0) {
            selectedDishes[dishId] -= 1;
			if (parentEl != null && selectedDishes[dishId] === 0)
			{
				parentEl.classList.remove("select-dish");
			}
        }
		
		
        updateQuantity(dishId);
    }

    function updateQuantity(dishId) {
        const quantityElement = document.querySelector(`.quantity[data-id="${dishId}"]`);
        if (quantityElement) {
            quantityElement.textContent = selectedDishes[dishId] || 0;
        }

        updateTotalPrice();
    }

    function updateTotalPrice() {
        let total = 0;
		const source = document.getElementById('id_order_type').value;
        Object.keys(selectedDishes).forEach((dishId) => {
            if (dishes[dishId]) {
				const dish = dishes[dishId];
				const price = dish.Price.length > 0 ? getDishPrice(dish, source) : 0;
                total += selectedDishes[dishId] * (price);
            }
        });
        document.getElementById("total-price").textContent = `Итого: ${total}`;
    }
	
	window.addSelectedDishes = function () {	
		removeEmptySelectedRows();
		
        Object.keys(selectedDishes).forEach((dishId, idx) => {
            const quantity = selectedDishes[dishId];
            if (quantity > 0) {
				console.log("Add dish to table. Index:", idx)
                addDishToTable(dishId, quantity, idx);
            }
        });
				
		// Генерируем событие об изменении заказа
        const event = new CustomEvent('selectedDishesChanged', {});
        document.dispatchEvent(event);

        closeModal();
    };
	
	function round(value, decimals = 2) {
		return Number(Math.round(value + 'e' + decimals) + 'e-' + decimals);
	}

	function fillDishRow(row, dishId, quantity) {
		const dishData = dishes[dishId];
		if (!dishData) return;

		const source = document.getElementById('id_order_type').value;
		const price = dishData.Price.length > 0 ? getDishPrice(dishData, source) : 0;
		const total = round(price * quantity);

		row.find("select[name$='-dish']").val(dishId).change();
		row.find("input[name$='-quantity']").val(quantity).change();
		row.find(".field-unit_price p").text(`${round(price)}`);
		row.find(".field-unit_amount p").text(`${total}`);
	}

	function addDishToTable(dishId, quantity) {
		const selects = document.querySelectorAll(".dynamic-orderdishes .field-dish select");
		const source = document.getElementById('id_order_type').value;

		for (let s of selects) {
			console.log("existing dish val", s.value);
			if (s.value === dishId) {
				const dishData = dishes[dishId];
				if (!dishData) return;

				const price = dishData.Price.length > 0 ? getDishPrice(dishData, source) : 0;
				const currentRow = $(s).closest('tr');

				if (currentRow.length) {
					const currentQuantity = parseInt(currentRow.find("input[name$='-quantity']").val(), 10);
					const newQuantity = currentQuantity + quantity;

					fillDishRow(currentRow, dishId, newQuantity);
				}
				return;
			}
		}

		const template = $("#" + options.prefix + "-empty");
		const row = template.clone(true);
		row.removeClass(options.emptyCssClass)
			.addClass(options.formCssClass)
			.attr("id", options.prefix + "-" + nextIndex);

		addInlineDeleteButton(row);
		row.find("*").each(function () {
			updateElementIndex(this, options.prefix, totalForms.val());
		});

		fillDishRow(row, dishId, quantity);
		row.insertBefore($(template));

		$(totalForms).val(parseInt(totalForms.val(), 10) + 1);
		nextIndex += 1;

		if ((maxForms.val() !== '') && (maxForms.val() - totalForms.val()) <= 0) {
			addButton.parent().hide();
		}

		toggleDeleteButtonVisibility(row.closest('.inline-group'));

		if (options.added) {
			options.added(row);
		}
		$(document).trigger('formset:added', [row, options.prefix]);
	}
	
	function addInlineDeleteButton(row) {
		if (row.is("tr")) {
			// If the forms are laid out in table rows, insert
			// the remove button into the last table cell:
			row.children(":last").append('<div><a class="' + options.deleteCssClass + '" href="#">' + options.deleteText + "</a></div>");
		} else if (row.is("ul") || row.is("ol")) {
			// If they're laid out as an ordered/unordered list,
			// insert an <li> after the last list item:
			row.append('<li><a class="' + options.deleteCssClass + '" href="#">' + options.deleteText + "</a></li>");
		} else {
			// Otherwise, just insert the remove button as the
			// last child element of the form's container:
			row.children(":first").append('<span><a class="' + options.deleteCssClass + '" href="#">' + options.deleteText + "</a></span>");
		}
		// Add delete handler for each row.
		row.find("a." + options.deleteCssClass).on('click', inlineDeleteHandler.bind(this));
	};

	function inlineDeleteHandler(e1) {
		e1.preventDefault();
		const deleteButton = $(e1.target);
		const row = deleteButton.closest('.' + options.formCssClass);
		const inlineGroup = row.closest('.inline-group');
		// Remove the parent form containing this button,
		// and also remove the relevant row with non-field errors:
		const prevRow = row.prev();
		if (prevRow.length && prevRow.hasClass('row-form-errors')) {
			prevRow.remove();
		}
		row.remove();
		nextIndex -= 1;
		// Pass the deleted form to the post-delete callback, if provided.
		if (options.removed) {
			options.removed(row);
		}
		$(document).trigger('formset:removed', [row, options.prefix]);
		// Update the TOTAL_FORMS form count.
		const forms = $("." + options.formCssClass);
		$("#id_" + options.prefix + "-TOTAL_FORMS").val(forms.length);
		// Show add button again once below maximum number.
		if ((maxForms.val() === '') || (maxForms.val() - forms.length) > 0) {
			addButton.parent().show();
		}
		// Hide the remove buttons if at min_num.
		toggleDeleteButtonVisibility(inlineGroup);
		// Also, update names and ids for all remaining form controls so
		// they remain in sequence:
		let i, formCount;
		const updateElementCallback = function() {
			updateElementIndex(this, options.prefix, i);
		};
		for (i = 0, formCount = forms.length; i < formCount; i++) {
			updateElementIndex($(forms).get(i), options.prefix, i);
			$(forms.get(i)).find("*").each(updateElementCallback);
		}
	};

	function toggleDeleteButtonVisibility(inlineGroup) {
		if ((minForms.val() !== '') && (minForms.val() - totalForms.val()) >= 0) {
			inlineGroup.find('.inline-deletelink').hide();
		} else {
			inlineGroup.find('.inline-deletelink').show();
		}
	};

    setTimeout(replaceButton, 100);
});
