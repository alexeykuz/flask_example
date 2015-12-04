@app.route('/admin/members', methods=['GET', 'POST'])
@admin_required
def admin_members_new():
    app_ctx = AppContext('admin', 'members')
    if request.method == 'GET':
        context = dict(app_ctx=app_ctx)
        locations = Program.objects(perm='r').distinct('location_id')
        location_ids = [L.location_id for L in locations]
        context['locations'] = Location.objects(id__in=location_ids).order_by(Location.name)
        context['categories'] = Program.CATEGORIES
        groups = set(Group.objects(member=app_ctx.logged_in, skip_group=False))
        groups = groups.union(set(Group.objects(
            members=app_ctx.logged_in, skip_auth=True)))
        groups = sorted(groups, key=lambda group: group.display_name.lower())
        context['groups'] = groups
        return render_template('admin/admin_people.html', **context)
    else:
        items = get_members(request)
        records_total = len(items)
        records_filtered = records_total
        items = Pagination(items).get_data()
        return jsonify(data=items, recordsTotal=records_total, recordsFiltered=records_filtered)
