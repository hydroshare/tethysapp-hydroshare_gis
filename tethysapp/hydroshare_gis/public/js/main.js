/*****************************************************************************
 * FILE:    Main
 * DATE:    2/2/2016
 * AUTHOR:  Shawn Crawley
 * COPYRIGHT: (c) 2015 Brigham Young University
 * LICENSE: BSD 2-Clause
 * CONTRIBUTIONS:   http://ignitersworld.com/lab/contextMenu.html
 *                  http://openlayers.org/
 *                  https://www.npmjs.com/package/reproject
 *
 *****************************************************************************/

/*****************************************************************************
 *                      LIBRARY WRAPPER
 *****************************************************************************/

// Global directives for JSLint/JSHint
/*global document, $, console, FormData, ol, window, setTimeout, reproject, proj4, pageX, pageY, clearInterval */

var HS_GIS = (function packageHydroShareGIS() {

    "use strict"; // And enable strict mode for this library

    /******************************************************
     ****************GLOBAL VARIABLES**********************
     ******************************************************/
    var currentLayers = [],
        layers,
        layersContextMenu,
        map,
        fileLoaded,
    // Functions
        addDataToMap,
        addDefaultBehaviorToAjax,
        addInitialEventListeners,
        areValidFiles,
        changeBaseMap,
        checkCsrfSafe,
        checkURLForParameters,
        editLayerName,
        getCookie,
        getFilesSize,
        hideProgressBar,
        initializeJqueryVariables,
        initializeLayersContextMenu,
        initializeMap,
        loadHSResource,
        populateHSResourceList,
        prepareFilesForAjax,
        reprojectExtents,
        updateProgressBar,
        updateUploadProgress,
        uploadFileButtonHandler,
        uploadResourceButtonHandler,
    //jQuery Selectors
        $currentLayersList,
        $emptyBar,
        $modalLoadFile,
        $modalLoadHSRes,
        $progressBar,
        $progressText,
        $uploadButton;

    /******************************************************
     **************FUNCTION DECLARATIONS*******************
     ******************************************************/

    addDataToMap = function (response) {
        var geoserverUrl,
            layerName,
            layerId,
            newLayer,
            rawLayerExtents,
            $firstLayerListElement;

        if (response.hasOwnProperty('success')) {
            layerName = response.layer_name;
            layerId = response.layer_id;
            rawLayerExtents = response.layer_extents;
            geoserverUrl = response.geoserver_url;

            newLayer = new ol.layer.Tile({
                extent: reprojectExtents(rawLayerExtents),
                source: new ol.source.TileWMS({
                    url: geoserverUrl + '/wms',
                    params: {'LAYERS': layerId, 'TILED': true},
                    serverType: 'geoserver'
                })
            });
            map.addLayer(newLayer);
            currentLayers.unshift(newLayer);
            $currentLayersList.prepend(
                '<li class="ui-state-default"><span class="layer-name">' + layerName + '</span><input type="text" class="edit-layer-name hidden" value="' + layerName + '"></li>'
            );
            $firstLayerListElement = $currentLayersList.find(':first-child');
            // Apply the dropdown-on-right-click menu to new layer in list
            $firstLayerListElement.contextMenu('menu', layersContextMenu, {
                triggerOn: 'click',
                displayAround: 'cursor',
                mouseClick: 'right'
            });
            $firstLayerListElement.find('.layer-name').on('dblclick', function () {
                var $layerNameSpan = $(this),
                    layerIndex = Number($currentLayersList.find('li').index($firstLayerListElement)) + 3;

                $layerNameSpan.addClass('hidden');
                $firstLayerListElement.find('input')
                    .removeClass('hidden')
                    .select()
                    .on('keyup', function (e) {
                        editLayerName(e, $(this), $layerNameSpan, layerIndex);
                    });
            });
            //} else {
            //    console.error('There is insufficient projection information to plot the shapefile.');
            //}
        }
    };

    addDefaultBehaviorToAjax = function () {
        // Add CSRF token to appropriate ajax requests
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                if (!checkCsrfSafe(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", getCookie("csrftoken"));
                }
            }
        });
    };

    addInitialEventListeners = function () {
        $('.basemap-option').on('click', changeBaseMap);

        $modalLoadFile.on('hidden.bs.modal', function () {
            $('#input-files').val('');
            hideProgressBar();
            $uploadButton
                .removeAttr('disabled')
                .text('Upload');
        });

        $modalLoadHSRes.on('hidden.bs.modal', function () {
            $uploadButton
                .removeAttr('disabled')
                .text('Upload');
        });

        $('#btn-upload-res').on('click', uploadResourceButtonHandler);

        $('#btn-upload-file').on('click', uploadFileButtonHandler);

    };

    areValidFiles = function (files) {
        var file,
            fileCount = 0,
            hasShp = false,
            hasShx = false,
            hasPrj = false,
            hasDbf = false,
            hasTif = false;

        for (file in files) {
            if (files.hasOwnProperty(file)) {
                if (++fileCount > 4) {
                    return false;
                }
                if (files.hasOwnProperty(file)) {
                    if (files[file].name.endsWith('.shp')) {
                        hasShp = true;
                    } else if (files[file].name.endsWith('.shx')) {
                        hasShx = true;
                    } else if (files[file].name.endsWith('.prj')) {
                        hasPrj = true;
                    } else if (files[file].name.endsWith('.dbf')) {
                        hasDbf = true;
                    } else if (files[file].name.endsWith('.tif')) {
                        hasTif = true;
                    }
                }
            }
        }
        return ((hasTif && fileCount === 1) || (hasShp && hasShx && hasPrj && hasDbf));
    };

    changeBaseMap = function () {
        $('.current-basemap-label').text('');
        $('.basemap-option').removeClass('selected-basemap-option');
        $(this).addClass('selected-basemap-option');
        $($(this).children()[0]).text(' (Current)');

        var style = $(this).attr('value'),
            i,
            ii = layers.length;

        for (i = 0; i < ii; ++i) {
            layers[i].set('visible', (layers[i].get('style') === style));
        }
    };

// Find if method is CSRF safe
    checkCsrfSafe = function (method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    };

    checkURLForParameters = function () {
        var transformToAssocArray = function (prmstr) {
                var i,
                    params = {},
                    prmArr = prmstr.split("&"),
                    tmpArr;

                for (i = 0; i < prmArr.length; i++) {
                    tmpArr = prmArr[i].split("=");
                    params[tmpArr[0]] = tmpArr[1];
                }
                return params;
            },
            getSearchParameters = function () {
                var prmstr = window.location.search.substr(1);
                return prmstr !== null && prmstr !== "" ? transformToAssocArray(prmstr) : {};
            },
            params = getSearchParameters();

        if (params.res_id !== undefined || params.res_id !== null) {
            if (params.src === 'hs') {
                loadHSResource(params.res_id);
            }
        }
    };

    editLayerName = function (e, $layerNameInput, $layerNameSpan, layerIndex) {
        if (e.which === 13) {  // Enter key
            $layerNameSpan.text($layerNameInput.val());
            $layerNameInput
                .addClass('hidden')
                .off('keyup');
            $layerNameSpan.removeClass('hidden');
            map.getLayers().item(layerIndex).set('name', $layerNameInput.val());
        } else if (e.which === 27) {  // Esc key
            $layerNameInput
                .addClass('hidden')
                .off('keyup')
                .val($layerNameSpan.text());
            $layerNameSpan.removeClass('hidden');
        }
    };

    getCookie = function (name) {
        var cookie,
            cookies,
            cookieValue = null,
            i;

        if (document.cookie && document.cookie !== '') {
            cookies = document.cookie.split(';');
            for (i = 0; i < cookies.length; i++) {
                cookie = $.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    };

    getFilesSize = function (files) {
        var file,
            fileSize = 0;

        for (file in files) {
            if (files.hasOwnProperty(file)) {
                fileSize += files[file].size;
            }
        }
        return fileSize;
    };

    hideProgressBar = function () {
        $progressBar.addClass('hidden');
        $progressText
            .addClass('hidden')
            .text('0%');
        $emptyBar.addClass('hidden');
    };

    initializeJqueryVariables = function () {
        $currentLayersList = $('#current-layers-list');
        $emptyBar = $('#empty-bar');
        $modalLoadFile = $('#modalLoadFile');
        $modalLoadHSRes = $('#modalLoadHSRes');
        $progressBar = $('#progress-bar');
        $progressText = $('#progress-text');
        $uploadButton = $('.btn-upload');
    };

    initializeLayersContextMenu = function () {
        layersContextMenu = [
            {
                name: 'Rename',
                title: 'Rename',
                fun: function (e) {
                    var clickedElement = e.trigger.context,
                        layerIndex = Number($currentLayersList.find('li').index(clickedElement)) + 3,
                        $LayerNameSpan = $(clickedElement).find('span');

                    $LayerNameSpan.addClass('hidden');
                    $(clickedElement).find('input')
                        .removeClass('hidden')
                        .select()
                        .on('keyup', function (e) {
                            editLayerName(e, $(this), $LayerNameSpan, layerIndex);
                        });
                }
            }, {
                name: 'Zoom to',
                title: 'Zoom to',
                fun: function (e) {
                    var clickedElement = e.trigger.context,
                        ceIndex = Number($currentLayersList.find('li').index(clickedElement)),
                        layerExtent = map.getLayers().item(ceIndex + 3).getExtent(); // Ignore 3 base maps
                    map.getView().fit(layerExtent, map.getSize());
                    if (map.getView().getZoom() > 16) {
                        map.getView().setZoom(16);
                    }
                }
            }, {
                name: 'Delete',
                title: 'Delete',
                fun: function (e) {
                    var clickedElement = e.trigger.context,
                        ceIndex = Number($currentLayersList.find('li').index(clickedElement));

                    map.getLayers().removeAt(ceIndex + 3);  // Ignore 3 base maps
                    $currentLayersList.find('li:nth-child(' + (ceIndex + 1) + ')').remove();
                }
            }
        ];
    };

    initializeMap = function () {
        // Base Layer options
        layers = [
            new ol.layer.Tile({
                style: 'Road',
                visible: false,
                source: new ol.source.MapQuest({layer: 'osm'})
            }),
            new ol.layer.Tile({
                style: 'Aerial',
                visible: false,
                source: new ol.source.MapQuest({layer: 'sat'})
            }),
            new ol.layer.Group({
                style: 'AerialWithLabels',
                visible: false,
                layers: [
                    new ol.layer.Tile({
                        source: new ol.source.MapQuest({layer: 'sat'})
                    }),
                    new ol.layer.Tile({
                        source: new ol.source.MapQuest({layer: 'hyb'})
                    })
                ]
            })
        ];

        map = new ol.Map({
            layers: layers,
            target: 'map',
            view: new ol.View({
                center: [0, 0],
                zoom: 2
            })
        });
    };

    loadHSResource = function (res_id) {
        $.ajax({
            type: 'GET',
            url: 'load-file',
            dataType: 'json',
            data: {
                'res_id': res_id
            },
            error: function () {
                console.error('Failure!');
            },
            success: function (response) {
                addDataToMap(response);
            }
        });
    };

    populateHSResourceList = function () {
        $.ajax({
            type: 'GET',
            url: 'get-hs-res-list',
            dataType: 'json',
            error: function () {
                console.error("The ajax request failed.");
            },
            success: function (response) {
                var resources,
                    resTableHtml = '<table><th></th><th>Title</th><th>Type</th>';

                if (response.hasOwnProperty('success')) {
                    if (response.hasOwnProperty('resources')) {
                        resources = JSON.parse(response.resources);
                        resources.forEach(function (resource) {
                            resTableHtml += '<tr>' +
                                '<td><input type="radio" name="resource" value="' + resource.id + '"></td>' +
                                '<td>' + resource.title + '</td>' +
                                '<td>' + resource.type + '</td>' +
                                '</tr>';
                        });
                        resTableHtml += '</table>';

                        $modalLoadHSRes.find('.modal-body').html(resTableHtml);
                        $('#btn-upload-res').removeClass('hidden');

                        $('tr').on('click', function () {
                            $(this)
                                .css({
                                    'background-color': '#1abc9c',
                                    'color': 'white'
                                })
                                .find('input').prop('checked', true);
                            $('tr').not($(this)).css({
                                'background-color': '',
                                'color': ''
                            });
                        });
                    }
                }
            }
        });
    };

    prepareFilesForAjax = function (files) {
        var file,
            data = new FormData();

        for (file in files) {
            if (files.hasOwnProperty(file)) {
                data.append('files', files[file]);
            }
        }
        return data;
    };

    reprojectExtents = function (rawExtents) {
        var crs,
            extentMaxX,
            extentMaxY,
            extentMinX,
            extentMinY,
            extents,
            tempCoord1,
            tempCoord2;

        extentMinX = Number(rawExtents.minx);
        extentMaxX = Number(rawExtents.maxx);
        extentMinY = Number(rawExtents.miny);
        extentMaxY = Number(rawExtents.maxy);

        crs = rawExtents.crs;
        proj4.defs('new_projection', crs);

        tempCoord1 = proj4(proj4('new_projection'), proj4('EPSG:3857'), [extentMinX, extentMinY]);
        tempCoord2 = proj4(proj4('new_projection'), proj4('EPSG:3857'), [extentMaxX, extentMaxY]);

        extents = tempCoord1.concat(tempCoord2);

        return extents;
    };

    updateProgressBar = function (value) {
        $progressBar.css('width', value);
        $progressText.text(value);
    };

    updateUploadProgress = function (fileSize, currProg) {
        var progress;

        currProg = currProg === undefined ? 0 : currProg;
        if (!fileLoaded) {
            currProg += 1000000;
            progress = Math.round(currProg / fileSize * 100);
            progress = progress > 100 ? 100 : progress;
            updateProgressBar(parseInt(progress, 10) + '%');
            setTimeout(function () {
                updateUploadProgress(fileSize, currProg);
            }, 1000);
        } else {
            updateProgressBar('100%');
        }
    };

    uploadFileButtonHandler = function () {
        var fileInputNode = $('#input-files')[0],
            files = fileInputNode.files,
            data,
            fileSize;

        if (!areValidFiles(files)) {
            console.error("Invalid files. Please include four total files: .shp, .shx, .prj, and .dbf.");
        } else {
            $uploadButton.attr('disabled', 'true');
            data = prepareFilesForAjax(files);
            fileSize = getFilesSize(files);
            fileLoaded = false;
            $.ajax({
                url: 'load-file/',
                type: 'POST',
                data: data,
                dataType: 'json',
                processData: false,
                contentType: false,
                error: function () {
                    $progressBar.addClass('hidden');
                    console.error("Error!");
                },
                success: function (response) {
                    fileLoaded = true;
                    updateProgressBar('100%');
                    addDataToMap(response);
                }
            });

            $emptyBar.removeClass('hidden');
            $progressBar.removeClass('hidden');
            $progressText.removeClass('hidden');
            updateUploadProgress(fileSize);
        }
    };

    uploadResourceButtonHandler = function () {
        $uploadButton.text('...')
            .attr('disabled', 'true');
        var res_id = $('input:checked').val();
        loadHSResource(res_id);
    };

    /*
     **************ONLOAD FUNCTION*******************
     */

    $(function () {
        initializeJqueryVariables();
        addDefaultBehaviorToAjax();
        initializeMap();
        populateHSResourceList();
        initializeLayersContextMenu();
        addInitialEventListeners();
        checkURLForParameters();

        $currentLayersList.sortable({
            placeholder: "ui-state-highlight",
            stop: function () {
                //TODO: Write change layer order function
            }
        });
        $currentLayersList.disableSelection();
    });
}());
