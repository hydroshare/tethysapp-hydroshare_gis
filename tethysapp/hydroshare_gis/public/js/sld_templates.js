var SLD_TEMPLATES = (function () {
    "use strict";

    var points,
        polygon,
        polyline,
        line,
        labels,
        addLabels,
        header,
        footer,
        fill,
        stroke;

    header =
        '<StyledLayerDescriptor version="1.0.0">' +
        '<NamedLayer>' +
        '<Name>{{layer-id}}</Name>' +
        '<UserStyle>' +
        '<FeatureTypeStyle>' +
        '<Rule>';

    footer =
        '</Rule>' +
        '</FeatureTypeStyle>' +
        '</UserStyle>' +
        '</NamedLayer>' +
        '</StyledLayerDescriptor>';

    fill =
        '<Fill>' +
        '<CssParameter name="fill">{{fill}}</CssParameter>' +
        '<CssParameter name="fill-opacity">{{fill-opacity}}</CssParameter>' +
        '</Fill>';

    stroke =
        '<Stroke>' +
        '<CssParameter name="stroke">{{stroke}}</CssParameter>' +
        '<CssParameter name="stroke-width">{{stroke-width}}</CssParameter>' +
        '<CssParameter name="stroke-opacity">{{stroke-opacity}}</CssParameter>' +
        '</Stroke>';

    line = '<LineSymbolizer>' + stroke + '</LineSymbolizer>';

    points =
        header +
        '<PointSymbolizer>' +
        '<Graphic>' +
        '<Mark>' +
        '<WellKnownName>{{point-shape}}</WellKnownName>' +
        fill +
        stroke +
        '</Mark>' +
        '<Size>{{point-size}}</Size>' +
        '</Graphic>' +
        '</PointSymbolizer>' +
        footer;

    polygon =
        header +
        '<PolygonSymbolizer>' +
        fill +
        '</PolygonSymbolizer>' +
        line +
        footer;

    polyline = header + line + footer;

    labels =
        '<TextSymbolizer>' +
        '<Label>' +
        '<PropertyName>{{label-field}}</PropertyName>' +
        '</Label>' +
        '<Font>' +
            //'<CssParameter name="font-family">Arial</CssParameter>' +
        '<CssParameter name="font-size">{{font-size}}</CssParameter>' +
            //'<CssParameter name="font-style">normal</CssParameter>' +
            //'<CssParameter name="font-weight">normal</CssParameter>' +
        '</Font>' +
            //'<LabelPlacement>' +
            //'<PointPlacement>' +
            //'<AnchorPoint>' +
            //'<AnchorPointX>0.5</AnchorPointX>' +
            //'<AnchorPointY>1.0</AnchorPointY>' +
            //'</AnchorPoint>' +
            //'<Displacement>' +
            //'<DisplacementX>0</DisplacementX>' +
            //'<DisplacementY>-12</DisplacementY>' +
            //'</Displacement>' +
            //'</PointPlacement>' +
            //'</LabelPlacement>' +
        '<Fill>' +
        '<CssParameter name="fill">{{font-fill}}</CssParameter>' +
        '<CssParameter name="fill-opacity">{{font-fill-opacity}}</CssParameter>' +
        '</Fill>' +
        '</TextSymbolizer>';

    addLabels = function (geometry) {
        var insertionIndex = geometry.indexOf('</Rule>');
        return geometry.slice(0, insertionIndex) + labels + geometry.slice(insertionIndex);
    };

    return {
        point: function (with_labels) {
            if (with_labels) {
                return addLabels(points);
            }
            return points;
        },
        polygon: function (with_labels) {
            if (with_labels) {
                return addLabels(polygon);
            }
            return polygon;
        },
        polyline: function (with_labels) {
            if (with_labels) {
                return addLabels(polyline);
            }
            return polyline;
        }
    };
}());