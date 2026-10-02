import assert from "node:assert/strict";
import test from "node:test";
import {
  moveBox,
  resizeBox,
  scalePoints,
  shiftPoints,
} from "../src/pdf_workbench/text_editor_frontend/marks.js";

test("move keeps the box on the page", () => {
  const moved = moveBox({x: 0.2, y: 0.3, width: 0.4, height: 0.2}, 0.9, -1);
  assert.equal(moved.x, 0.6);
  assert.equal(moved.y, 0);
  assert.equal(moved.width, 0.4);
});

test("resize uses the dragged corner and keeps a minimum size", () => {
  const start = {x: 0.2, y: 0.2, width: 0.3, height: 0.3};
  const east = resizeBox(start, "se", {x: 0.8, y: 0.7});
  assert.equal(east.x, 0.2);
  assert.equal(east.y, 0.2);
  assert.ok(Math.abs(east.width - 0.6) < 1e-9);
  assert.ok(Math.abs(east.height - 0.5) < 1e-9);

  const pinched = resizeBox(start, "se", {x: 0.2, y: 0.2});
  assert.ok(Math.abs(pinched.width - 0.005) < 1e-9);
  assert.ok(Math.abs(pinched.height - 0.005) < 1e-9);
});

test("shift moves a stroke until it hits the page edge", () => {
  const shifted = shiftPoints([[0.1, 0.2], [0.4, 0.5]], -1, 0.1);
  assert.ok(Math.abs(shifted[0][0]) < 1e-9);
  assert.ok(Math.abs(shifted[0][1] - 0.3) < 1e-9);
  assert.ok(Math.abs(shifted[1][0] - 0.3) < 1e-9);
  assert.equal(shifted[1][1], 0.6);
});

test("scale stretches a stroke inside the new box", () => {
  const scaled = scalePoints(
    [[0.2, 0.2], [0.4, 0.4]],
    {x: 0.2, y: 0.2, width: 0.2, height: 0.2},
    {x: 0.1, y: 0.1, width: 0.4, height: 0.4},
  );
  assert.deepEqual(scaled, [[0.1, 0.1], [0.5, 0.5]]);
});
