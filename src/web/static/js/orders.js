let currentlyShown = [];

$(document).ready(function() {
    const ITEMS_PER_PAGE = 10;
    
    // Make currentlyShown a global variable with a proper initial value
    window.currentlyShown = ITEMS_PER_PAGE;
    
    // Store original orders data if table exists
    const ordersTableBody = $('#ordersTableBody');
    if (ordersTableBody.length) {
        // Store original orders in a global variable
        window.originalOrders = Array.from(ordersTableBody.find('tr')).map(row => ({
            element: row,
            orderName: $(row).find('td:nth-child(2)').text().toLowerCase(),
            status: $(row).find('.status-select').length ? 
                   $(row).find('.status-select').val().toLowerCase() :
                   $(row).find('td:nth-child(6)').text().trim().toLowerCase(),
            date: new Date($(row).find('td:nth-child(7)').text())
        }));

        // Apply filters automatically when any filter changes
        $("#orderSearch, #authorSearch, #statusFilter, #dateStart, #dateEnd").on("change keyup", function() {
            // Add a small delay to prevent too many requests while typing
            clearTimeout(window.filterTimeout);
            window.filterTimeout = setTimeout(function() {
                applyAllFilters();
            }, 500);
        });
        
        // Reset filters button
        $("#resetFiltersBtn").on("click", function() {
            $("#orderSearch").val("");
            $("#authorSearch").val("");
            $("#statusFilter").val("");
            $("#dateStart").val("");
            $("#dateEnd").val("");
            applyAllFilters();
        });
        
        // Username suggestions for author search
        setupAuthorSuggestions();
    }

    // Update the updateShowMoreButtonVisibility function
    function updateShowMoreButtonVisibility() {
        const $showMoreBtn = $('#showMoreBtn');
        if (!$showMoreBtn.length) return;
        
        const visibleItems = $(".order-item:visible").length;
        const totalItems = $(".order-item").length;
        
        // Show button if there are exactly ITEMS_PER_PAGE items visible
        // (indicating there might be more to load)
        if (visibleItems === ITEMS_PER_PAGE) {
            $showMoreBtn.show();
        } else {
            $showMoreBtn.hide();
        }
    }

    // Fix the Show More button functionality
    $('#showMoreBtn').off('click').on('click', function() {
        const offset = $('.order-item').length;
        const searchTerm = $('#orderSearch').val();
        const authorTerm = $('#authorSearch').val();
        const status = $('#statusFilter').val();
        const dateStart = $('#dateStart').val();
        const dateEnd = $('#dateEnd').val();
        
        // Show loading state
        $(this).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...');
        $(this).prop('disabled', true);
        
        // Make AJAX request to load more orders
        $.get('/load_more_orders', {
            offset: offset,
            search: searchTerm,
            author: authorTerm,
            status: status,
            date_start: dateStart,
            date_end: dateEnd
        })
        .done(function(response) {
            if (response.success && response.orders.length > 0) {
                // Append new orders to the table
                response.orders.forEach(function(order, index) {
                    const sessionData = getSessionData();
                    const statusHtml = (sessionData.admin || sessionData.username === order.order_assignee) ?
                        `<select class="form-control status-select" data-order-id="${order.id}">
                            <option value="pending" ${order.status.toLowerCase() === 'pending' ? 'selected' : ''}>Pending</option>
                            <option value="ordered" ${order.status.toLowerCase() === 'ordered' ? 'selected' : ''}>Ordered</option>
                            <option value="rejected" ${order.status.toLowerCase() === 'rejected' ? 'selected' : ''}>Rejected</option>
                        </select>` :
                        order.status;
                    
                    const actionsHtml = `
                        <button class="btn btn-sm btn-info" onclick="showOrderDetails(${order.id})">Details</button>
                        ${sessionData.username === order.order_author ? `
                            <button class="btn btn-sm btn-warning" onclick="editOrder(${order.id})">Edit</button>
                            <button class="btn btn-sm btn-danger" onclick="deleteOrder(${order.id})">Delete</button>
                        ` : ''}`;
                    
                    const newRow = `
                        <tr class="order-item" data-status="${order.status.toLowerCase()}">
                            <td class="row-number text-center align-middle py-3">${offset + index + 1}</td>
                            <td class="align-middle py-3">${order.order_name}</td>
                            <td class="text-center align-middle py-3">${order.quantity}</td>
                            <td class="align-middle py-3">${order.order_assignee}</td>
                            <td class="align-middle py-3">${order.order_author}</td>
                            <td class="align-middle py-3">${statusHtml}</td>
                            <td class="align-middle py-3">${order.date}</td>
                            <td class="text-center align-middle py-3">${actionsHtml}</td>
                        </tr>`;
                    
                    $('#ordersTableBody').append(newRow);
                });
                
                // Update button state
                $('#showMoreBtn').html('<i class="bi bi-arrow-down-circle me-1"></i> Show More');
                $('#showMoreBtn').prop('disabled', false);
                
                // Show button only if there are more orders to load
                if (response.orders.length < ITEMS_PER_PAGE) {
                    $('#showMoreBtn').hide();
                }
                
                // Initialize status selects for new rows
                initializeStatusSelects();
            } else {
                // No more orders to load
                $('#showMoreBtn').hide();
            }
        })
        .fail(function() {
            // Reset button state
            $('#showMoreBtn').html('<i class="bi bi-arrow-down-circle me-1"></i> Show More');
            $('#showMoreBtn').prop('disabled', false);
            showAlert('Failed to load more orders', 'danger');
        });
    });
    
    // Initialize status select handlers
    initializeStatusSelects();
});

// Function to set up author suggestions
function setupAuthorSuggestions() {
    const authorInput = $("#authorSearch");
    const suggestionsList = $("#author_suggestions");
    
    authorInput.on("input focus", function() {
        const query = $(this).val();
        const lastQuery = query.split(',').pop().trim();
        
        if (lastQuery.length < 1) {
            suggestionsList.hide();
            return;
        }
        
        // Make AJAX request to search for usernames
        $.ajax({
            url: "/username_search",
            method: "POST",
            data: { text: lastQuery },
            success: function(response) {
                if (response.length > 0) {
                    // Build suggestions list
                    let html = '';
                    response.forEach(function(user) {
                        html += `<a class="dropdown-item" href="#" data-username="${user[0]}">${user[0]}</a>`;
                    });
                    
                    suggestionsList.html(html);
                    suggestionsList.show();
                    
                    // Handle clicking on a suggestion
                    $(".dropdown-item", suggestionsList).on("click", function(e) {
                        e.preventDefault();
                        const username = $(this).data("username");
                        
                        // Get current input value and replace the last part
                        let currentValue = authorInput.val();
                        const parts = currentValue.split(',');
                        parts.pop(); // Remove the last part (what user was typing)
                        
                        // Add the selected username
                        if (parts.length > 0) {
                            currentValue = parts.join(',') + ', ' + username;
                        } else {
                            currentValue = username;
                        }
                        
                        authorInput.val(currentValue + ', ');
                        suggestionsList.hide();
                        authorInput.focus();
                        
                        // Trigger change to apply filters
                        authorInput.trigger('change');
                    });
                } else {
                    suggestionsList.hide();
                }
            }
        });
    });
    
    // Hide suggestions when clicking outside
    $(document).on("click", function(e) {
        if (!$(e.target).closest("#authorSearch, #author_suggestions").length) {
            suggestionsList.hide();
        }
    });
}

// Function to apply all filters
window.applyAllFilters = function() {
    const searchTerm = $("#orderSearch").val().toLowerCase();
    const authorTerm = $("#authorSearch").val().toLowerCase();
    const status = $("#statusFilter").val();
    const dateStart = $("#dateStart").val();
    const dateEnd = $("#dateEnd").val();
    
    // Show loading state
    $('#ordersTableBody').html('<tr><td colspan="8" class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></td></tr>');
    
    // Reset to first page when applying filters
    $.get('/orders', {
        search: searchTerm,
        author: authorTerm,
        status: status,
        date_start: dateStart,
        date_end: dateEnd,
        format: 'json'  // Add this to indicate we want JSON response
    })
    .done(function(response) {
        // Clear the table body
        $('#ordersTableBody').empty();
        
        if (response.orders && response.orders.length > 0) {
            // Add new rows
            response.orders.forEach(function(order, index) {
                const sessionData = getSessionData();
                const statusHtml = (sessionData.admin || sessionData.username === order.order_assignee) ?
                    `<select class="form-control status-select" data-order-id="${order.id}">
                        <option value="pending" ${order.status.toLowerCase() === 'pending' ? 'selected' : ''}>Pending</option>
                        <option value="ordered" ${order.status.toLowerCase() === 'ordered' ? 'selected' : ''}>Ordered</option>
                        <option value="rejected" ${order.status.toLowerCase() === 'rejected' ? 'selected' : ''}>Rejected</option>
                    </select>` :
                    order.status;
                
                const actionsHtml = `
                    <button class="btn btn-sm btn-info" onclick="showOrderDetails(${order.id})">Details</button>
                    ${sessionData.username === order.order_author ? `
                        <button class="btn btn-sm btn-warning" onclick="editOrder(${order.id})">Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteOrder(${order.id})">Delete</button>
                    ` : ''}`;
                
                const newRow = `
                    <tr class="order-item" data-status="${order.status.toLowerCase()}">
                        <td class="row-number text-center align-middle py-3">${index + 1}</td>
                        <td class="align-middle py-3">${order.order_name}</td>
                        <td class="text-center align-middle py-3">${order.quantity}</td>
                        <td class="align-middle py-3">${order.order_assignee}</td>
                        <td class="align-middle py-3">${order.order_author}</td>
                        <td class="align-middle py-3">${statusHtml}</td>
                        <td class="align-middle py-3">${order.date}</td>
                        <td class="text-center align-middle py-3">${actionsHtml}</td>
                    </tr>`;
                
                $('#ordersTableBody').append(newRow);
            });
            
            // Show/hide "Show More" button based on number of results
            if (response.orders.length === 10) {
                $('#showMoreBtn').show();
            } else {
                $('#showMoreBtn').hide();
            }
            
            // Reinitialize status select handlers
            initializeStatusSelects();
        } else {
            // Show "no results" message
            $('#ordersTableBody').html('<tr><td colspan="8" class="text-center">No orders found</td></tr>');
            $('#showMoreBtn').hide();
        }
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.error('Filter request failed:', textStatus, errorThrown);
        showAlert('Failed to apply filters: ' + (errorThrown || 'Unknown error'), 'danger');
        $('#ordersTableBody').html('<tr><td colspan="8" class="text-center">Error loading orders</td></tr>');
    });
};

// Function to initialize status select handlers
function initializeStatusSelects() {
    $('.status-select').off('change').on('change', function() {
        const orderId = $(this).data('order-id');
        const newStatus = $(this).val();
        
        $.post('/update_order_status', {
            order_id: orderId,
            status: newStatus
        })
        .done(function(response) {
            if (response.success) {
                // Remove any existing success alerts before showing a new one
                $('.alert-success').remove();
            } else {
                showAlert('Failed to update order status: ' + (response.error || 'Unknown error'), 'danger');
            }
        })
        .fail(function() {
            showAlert('Failed to update order status', 'danger');
        });
    });
}

// Function to get session data
function getSessionData() {
    // This function should be implemented to return the current user's session data
    // For now, we'll just return a placeholder
    return {
        username: window.currentUsername || '',
        admin: window.isAdmin || false
    };
}

// Show order details function
window.showOrderDetails = function(orderId) {
    // Fetch order details and show in modal
    $.get(`/get_order_details/${orderId}`)
        .done(function(order) {
            let detailsHtml = `
                <div class="mb-3">
                    <h6 class="fw-bold">Order Name:</h6>
                    <p>${order.order_name}</p>
                </div>
                <div class="mb-3">
                    <h6 class="fw-bold">Quantity:</h6>
                    <p>${order.quantity}</p>
                </div>
                <div class="mb-3">
                    <h6 class="fw-bold">Assignee:</h6>
                    <p>${order.order_assignee}</p>
                </div>
                <div class="mb-3">
                    <h6 class="fw-bold">Author:</h6>
                    <p>${order.order_author}</p>
                </div>
                <div class="mb-3">
                    <h6 class="fw-bold">Status:</h6>
                    <p>${order.status}</p>
                </div>
                <div class="mb-3">
                    <h6 class="fw-bold">Date:</h6>
                    <p>${order.date}</p>
                </div>
            `;
            
            if (order.link) {
                detailsHtml += `
                    <div class="mb-3">
                        <h6 class="fw-bold">Link:</h6>
                        <p><a href="${order.link}" target="_blank">${order.link}</a></p>
                    </div>
                `;
            }
            
            if (order.note) {
                detailsHtml += `
                    <div class="mb-3">
                        <h6 class="fw-bold">Note:</h6>
                        <p>${order.note}</p>
                    </div>
                `;
            }
            
            $('#orderDetailsContent').html(detailsHtml);
            $('#orderDetailsModal').modal('show');
        })
        .fail(function() {
            showAlert('Failed to load order details', 'danger');
        });
};

// Edit order function
window.editOrder = function(orderId) {
    // Fetch order details and populate the edit form
    $.get(`/get_order_details/${orderId}`)
        .done(function(order) {
            $('#edit_order_id').val(order.id);
            $('#edit_order_name').val(order.order_name);
            $('#edit_link').val(order.link || '');
            $('#edit_quantity').val(order.quantity);
            $('#edit_note').val(order.note || '');
            
            // Show the edit modal
            $('#editOrderModal').modal('show');
        })
        .fail(function() {
            showAlert('Failed to load order details for editing', 'danger');
        });
};

// Delete order function
window.deleteOrder = function(orderId) {
    // Set the order ID in the delete confirmation modal
    $('#delete_order_id').val(orderId);
    
    // Show the delete confirmation modal
    $('#deleteOrderModal').modal('show');
};

// Make showAlert globally accessible too
window.showAlert = function(message, type) {
    // Remove any existing alerts of the same type
    $('.alert-' + type).remove();
    
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    // Add the new alert at the top of the container
    $('.container').prepend(alertHtml);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        $('.alert-' + type).alert('close');
    }, 5000);
};

// Add this new function to check if an order matches the current filters
function isOrderMatchingFilters($orderRow) {
    const searchTerm = $('#orderSearch').val().toLowerCase();
    const authorTerm = $('#authorSearch').val().toLowerCase();
    const statusFilter = $('#statusFilter').val().toLowerCase();
    const dateStart = $('#dateStart').val() ? new Date($('#dateStart').val()) : null;
    const dateEnd = $('#dateEnd').val() ? new Date($('#dateEnd').val()) : null;

    if (dateEnd) dateEnd.setHours(23, 59, 59, 999);

    // Get order data
    const orderName = $orderRow.find('td:nth-child(2)').text().toLowerCase();
    const orderAuthor = $orderRow.find('td:nth-child(5)').text().toLowerCase();
    const rowStatus = $orderRow.attr('data-status');
    const rowDateText = $orderRow.find('td:nth-child(7)').text().trim();
    const rowDate = new Date(rowDateText);

    // Check if order matches all filters
    const matchesSearch = searchTerm === "" || orderName.includes(searchTerm);
    
    // Handle multiple authors separated by commas
    const matchesAuthor = authorTerm === "" || 
                          authorTerm.split(',').some(author => {
                              const trimmedAuthor = author.trim();
                              return trimmedAuthor === "" || orderAuthor.includes(trimmedAuthor);
                          });
                          
    const matchesStatus = statusFilter === "" || rowStatus === statusFilter;
    const matchesDateRange = (!dateStart || rowDate >= dateStart) && 
                            (!dateEnd || rowDate <= dateEnd);

    return matchesSearch && matchesAuthor && matchesStatus && matchesDateRange;
}