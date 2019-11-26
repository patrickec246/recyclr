// globals
var canvas = document.getElementById('polyCanvas');
var ctx = canvas.getContext("2d");
var current_img = "";
var mgr = new ShapeManager();

// set load hooks
window.onload = reload_canvas;
window,onresize = reload_canvas;

// working vars
var selected_shape = null;
var base_img = new Image();
var last_img = "";
var canvas_down = false;
var added_shape = null;
var add_shape = false;

// when the canvas image is updated, redraw the image
base_img.onload = function() {
	ctx.drawImage(base_img, 0, 0, canvas.width, canvas.height);
	reload_canvas();
}

//
// Drawing utilities
//

function delete_selected_shape() {
	if (selected_shape) {
		mgr.delete_shape(selected_shape);
		selected_shape = null;
		shapeDock.style.display = 'none';
		reload_canvas();
	}
}

function update_selected_shape() {
	if (selected_shape) {
		selected_shape.label = document.getElementById('typeLabel').value;
		shapeDock.style.display = 'none';
		reload_canvas();
	}
}

// redraw the canvas, background img, and polygons
function reload_canvas() {
	// draw bg img
	if (last_img != current_img) {
		last_img = current_img;
		base_img.src = current_img;
	}

	ctx.drawImage(base_img, 0, 0, canvas.width - 200, canvas.height);

	// draw polygons
	mgr.draw_shapes(ctx);
}

// initiates addition of a new polygon
function addShape() {
	if (!add_shape) {
		add_shape = true;
		added_shape = new Shape();
	}
}

//
// Canvas ('canvas') asynchronous hooks
//

canvas.onmousedown = function(e) {
	if (add_shape) {
		added_shape.add_point(e.offsetX, e.offsetY);

		if (added_shape.num_points() == 4) {
			mgr.add_shape(added_shape);
			added_shape = null;
			add_shape = false;
		}

		reload_canvas();
	}

	if (mgr.replace_closest_point(e.offsetX, e.offsetY)) {
		reload_canvas();
	}

	canvas_down = true;
}

canvas.onmouseup = function(e) {
	canvas_down = false;
}

canvas.onmousemove = function(e) {
	if (canvas_down) {
		if (mgr.replace_closest_point(e.offsetX, e.offsetY, 20)) {
			reload_canvas();
		}
	}
}

canvas.onclick = function(e) {
	var selection = mgr.select_shape(e.offsetX, e.offsetY);

	if (selection) {
		selected_shape = selection;
		var dockLoc = selection.calculate_dock_location(300, 215);

		shapeDock.style.left = dockLoc[0];
		shapeDock.style.top  = dockLoc[1];
		shapeDock.style.display = 'block';

		document.getElementById('typeLabel').value = selection.label;
	}
}

//
// Dock operations
//

var closeBtn = document.getElementById("closeBtn");
var shapeDock = document.getElementById("shapeDock");

closeBtn.onclick = function(e) {
	if (shapeDock.style.display == 'none') {
		shapeDock.style.display = 'block';
	} else {
		shapeDock.style.display = 'none';
	}
}
