"""
Unit tests for the Formats compiler module.
Tests data source resolution, binding engine, and render props compilation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from services.formats.compiler import (
    get_path,
    set_path,
    render_template,
    apply_transform,
    apply_bindings,
    create_base_render_props,
    infer_duration_from_script,
    resolve_data_sources,
    compile_run,
)
from services.formats.schema import RenderProps, CompileResult, VideoConfig


class TestGetPath:
    """Tests for dot-path navigation."""
    
    def test_simple_path(self):
        obj = {"a": {"b": {"c": 123}}}
        assert get_path(obj, "a.b.c") == 123
    
    def test_array_index(self):
        obj = {"items": [{"name": "first"}, {"name": "second"}]}
        assert get_path(obj, "items[0].name") == "first"
        assert get_path(obj, "items[1].name") == "second"
    
    def test_missing_path_returns_none(self):
        obj = {"a": {"b": 1}}
        assert get_path(obj, "a.c.d") is None
        assert get_path(obj, "x.y.z") is None
    
    def test_empty_path_returns_object(self):
        obj = {"a": 1}
        assert get_path(obj, "") == obj
    
    def test_array_out_of_bounds(self):
        obj = {"items": [1, 2]}
        assert get_path(obj, "items[5]") is None
    
    def test_none_object(self):
        assert get_path(None, "a.b") is None


class TestSetPath:
    """Tests for setting nested values."""
    
    def test_simple_set(self):
        obj = {}
        set_path(obj, "a.b.c", 123)
        assert obj == {"a": {"b": {"c": 123}}}
    
    def test_overwrite_existing(self):
        obj = {"a": {"b": 1}}
        set_path(obj, "a.b", 2)
        assert obj["a"]["b"] == 2
    
    def test_create_intermediate_keys(self):
        obj = {"x": 1}
        set_path(obj, "a.b.c.d", "value")
        assert obj["a"]["b"]["c"]["d"] == "value"
        assert obj["x"] == 1


class TestRenderTemplate:
    """Tests for template string rendering."""
    
    def test_simple_template(self):
        result = render_template("Hello {{name}}", {"name": "World"})
        assert result == "Hello World"
    
    def test_nested_path(self):
        ctx = {"user": {"profile": {"name": "Alice"}}}
        result = render_template("Hi {{user.profile.name}}", ctx)
        assert result == "Hi Alice"
    
    def test_missing_value_empty_string(self):
        result = render_template("Hello {{missing}}", {})
        assert result == "Hello "
    
    def test_multiple_placeholders(self):
        result = render_template("{{a}} and {{b}}", {"a": "X", "b": "Y"})
        assert result == "X and Y"
    
    def test_whitespace_in_placeholder(self):
        result = render_template("{{ name }}", {"name": "Test"})
        assert result == "Test"


class TestApplyTransform:
    """Tests for binding transforms."""
    
    def test_pick_transform(self):
        transform = {"type": "pick", "path": "data.value"}
        value = {"data": {"value": 42}}
        result = apply_transform(transform, value, {})
        assert result == 42
    
    def test_map_transform(self):
        transform = {
            "type": "map",
            "mapTemplate": {"id": "{{item.id}}", "label": "{{item.name}}"}
        }
        value = [{"id": 1, "name": "One"}, {"id": 2, "name": "Two"}]
        result = apply_transform(transform, value, {})
        assert result == [{"id": "1", "label": "One"}, {"id": "2", "label": "Two"}]
    
    def test_template_transform(self):
        transform = {"type": "template", "template": "Topic: {{value}}"}
        result = apply_transform(transform, "AI News", {})
        assert result == "Topic: AI News"
    
    def test_coerce_to_string(self):
        transform = {"type": "coerce", "to": "string"}
        assert apply_transform(transform, 123, {}) == "123"
    
    def test_coerce_to_number(self):
        transform = {"type": "coerce", "to": "number"}
        assert apply_transform(transform, "42.5", {}) == 42.5
    
    def test_coerce_to_boolean(self):
        transform = {"type": "coerce", "to": "boolean"}
        assert apply_transform(transform, "yes", {}) == True
        assert apply_transform(transform, 0, {}) == False
    
    def test_default_transform_with_value(self):
        transform = {"type": "default", "value": "fallback"}
        assert apply_transform(transform, "actual", {}) == "actual"
    
    def test_default_transform_with_none(self):
        transform = {"type": "default", "value": "fallback"}
        assert apply_transform(transform, None, {}) == "fallback"


class TestApplyBindings:
    """Tests for the binding engine."""
    
    def test_simple_binding(self):
        bindings = [{"target": "topic", "from": "data.name"}]
        resolved = {"data": {"name": "Test Topic"}}
        base = {}
        
        result = apply_bindings(bindings, resolved, base)
        assert result["topic"] == "Test Topic"
    
    def test_nested_target(self):
        bindings = [{"target": "script.hook", "from": "data.hook"}]
        resolved = {"data": {"hook": "Did you know?"}}
        base = {"script": {}}
        
        result = apply_bindings(bindings, resolved, base)
        assert result["script"]["hook"] == "Did you know?"
    
    def test_binding_with_transform(self):
        bindings = [{
            "target": "topic",
            "from": "raw",
            "transform": {"type": "template", "template": "Topic: {{value}}"}
        }]
        resolved = {"raw": "AI"}
        base = {}
        
        result = apply_bindings(bindings, resolved, base)
        assert result["topic"] == "Topic: AI"
    
    def test_missing_optional_binding(self):
        bindings = [{"target": "optional", "from": "missing.path", "required": False}]
        resolved = {}
        base = {"existing": "value"}
        
        result = apply_bindings(bindings, resolved, base)
        assert "optional" not in result
        assert result["existing"] == "value"
    
    def test_missing_required_binding_raises(self):
        bindings = [{"target": "required", "from": "missing.path", "required": True}]
        resolved = {}
        base = {}
        
        with pytest.raises(ValueError, match="Missing required binding"):
            apply_bindings(bindings, resolved, base)


class TestCreateBaseRenderProps:
    """Tests for base render props creation."""
    
    def test_creates_required_structure(self):
        format_def = {
            "id": "test_format",
            "defaults": {"params": {"captionStyle": "clean_subs"}}
        }
        
        result = create_base_render_props(format_def, "run-123")
        
        assert result["topic"] == "Untitled"
        assert "script" in result
        assert "audio" in result
        assert "visuals" in result
        assert "style" in result
        assert result["meta"]["run_id"] == "run-123"
        assert result["meta"]["format_id"] == "test_format"
    
    def test_applies_default_params(self):
        format_def = {
            "id": "test",
            "defaults": {"params": {"captionStyle": "bold_pop", "hookIntensity": 0.9}}
        }
        
        result = create_base_render_props(format_def, "run-1")
        assert result["style"]["caption_style"] == "bold_pop"
    
    def test_includes_variant_id(self):
        format_def = {"id": "test", "defaults": {}}
        result = create_base_render_props(format_def, "run-1", "shorts_9x16")
        assert result["meta"]["variant_id"] == "shorts_9x16"


class TestInferDurationFromScript:
    """Tests for duration inference from script segments."""
    
    def test_infers_from_segments(self):
        render_props = {
            "script": {
                "segments": [
                    {"id": "1", "t_start_sec": 0, "t_end_sec": 10},
                    {"id": "2", "t_start_sec": 10, "t_end_sec": 25},
                    {"id": "3", "t_start_sec": 25, "t_end_sec": 40},
                ]
            }
        }
        
        duration = infer_duration_from_script(render_props, 60)
        assert duration == 40.5  # max end + 0.5
    
    def test_fallback_when_no_segments(self):
        render_props = {"script": {"segments": []}}
        duration = infer_duration_from_script(render_props, 55)
        assert duration == 55
    
    def test_fallback_when_no_timestamps(self):
        render_props = {
            "script": {
                "segments": [{"id": "1", "text": "No timing"}]
            }
        }
        duration = infer_duration_from_script(render_props, 45)
        assert duration == 45


class TestResolveDataSources:
    """Tests for data source resolution."""
    
    @pytest.mark.asyncio
    async def test_local_library_source(self):
        sources = [{
            "id": "memes",
            "type": "local_library",
            "libraryId": "meme_bank",
            "filter": {"limit": 5}
        }]
        libraries = {
            "meme_bank": {
                "items": [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}, {"id": 6}]
            }
        }
        
        result = await resolve_data_sources(sources, {}, libraries=libraries)
        
        assert "memes" in result
        assert len(result["memes"]["items"]) == 5
    
    @pytest.mark.asyncio
    async def test_missing_library_returns_warning(self):
        sources = [{"id": "missing", "type": "local_library", "libraryId": "nonexistent"}]
        
        result = await resolve_data_sources(sources, {}, libraries={})
        
        assert "warning" in result["missing"]
    
    @pytest.mark.asyncio
    async def test_unknown_source_type(self):
        sources = [{"id": "unknown", "type": "unknown_type"}]
        
        result = await resolve_data_sources(sources, {})
        
        assert "error" in result["unknown"]


class TestCompileRun:
    """Integration tests for the full compile flow."""
    
    @pytest.mark.asyncio
    async def test_basic_compile(self):
        format_def = {
            "id": "test_format",
            "composition": {
                "remotionCompositionId": "TestComp",
                "fps": 30,
                "width": 1080,
                "height": 1920,
                "defaultDurationSec": 30
            },
            "defaults": {
                "params": {},
                "providers": {}
            },
            "dataSources": [],
            "bindings": []
        }
        
        result = await compile_run(format_def, "run-123", {})
        
        assert isinstance(result, CompileResult)
        assert result.video_config.fps == 30
        assert result.video_config.width == 1080
        assert result.video_config.height == 1920
        assert result.render_props.meta.run_id == "run-123"
    
    @pytest.mark.asyncio
    async def test_compile_with_variant(self):
        format_def = {
            "id": "test",
            "composition": {
                "remotionCompositionId": "Test",
                "fps": 30,
                "width": 1080,
                "height": 1920,
                "defaultDurationSec": 60,
                "variantSets": [
                    {"id": "square", "width": 1080, "height": 1080, "maxDurationSec": 30}
                ]
            },
            "defaults": {},
            "dataSources": [],
            "bindings": []
        }
        
        result = await compile_run(format_def, "run-1", {"variantId": "square"})
        
        assert result.video_config.width == 1080
        assert result.video_config.height == 1080
        assert result.render_props.meta.variant_id == "square"
    
    @pytest.mark.asyncio
    async def test_compile_applies_bindings(self):
        format_def = {
            "id": "test",
            "composition": {
                "remotionCompositionId": "Test",
                "fps": 30,
                "width": 1080,
                "height": 1920,
                "defaultDurationSec": 30
            },
            "defaults": {},
            "dataSources": [
                {"id": "local", "type": "local_library", "libraryId": "test_lib"}
            ],
            "bindings": [
                {"target": "topic", "from": "local.items[0].name"}
            ]
        }
        libraries = {"test_lib": {"items": [{"name": "Test Topic"}]}}
        
        result = await compile_run(format_def, "run-1", {}, libraries=libraries)
        
        assert result.render_props.topic == "Test Topic"
