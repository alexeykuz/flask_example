class Project(DB.Model, CurriculumElementMixin, CurriculumElementStatusMixin, RequirementMixin):
    CATEGORIES = ['challenge', 'contraption', 'game']

    DIFFICULTIES = ['EASY', 'MODERATE', 'HARD']

    program_id = DB.Column(DB.String, DB.ForeignKey('program.id'))

    difficulty = fields.StringField(choices=tupelate(DIFFICULTIES),
                                    default='EASY')

    sku = fields.IntField(default=0)
    parent_sku = fields.IntField(default=0)
    purpose = fields.StringField()
    constraints = fields.StringField()
    copy_count = fields.IntField(default=0)
    # notes, creators, components, files are defined in rels.py

    meta = {'queryset_class': ProjectQuerySet}

    @staticmethod
    def get_candidate_components():
        return Component.objects()

    @staticmethod
    def get_candidate_files(self):
        return ProjectFile.objects()

    @staticmethod
    def get_candidate_creators(self):
        return Member.objects()

    @property
    def parent(self):
        try:
            return Project.objects.get(sku=self.parent_sku)
        except Project.DoesNotExist:
            return None

    def my_kids(self, parent):
        """Helper method to get the display for the
        kids of the parent on this project

        """

        result = ' and '.join([c.first_name for c in self.creators if c.creator == parent])
        if result == '':
            return 'your child'
        return result

    def make_copy(self):
        """create a copy of key things"""
        new_project = Project.objects.create(title=self.title,
                                             description=self.description,
                                             tags=self.tags,
                                             constraints=self.constraints,
                                             components=self.components,
                                             level=self.level,
                                             category=self.category,
                                             parent_sku=self.sku)
        if self.program:
            new_project.program = self.program
            new_project.save(skip_auth=True)
        self.copy_count += 1
        self.save(skip_auth=True)
        return new_project

    @property
    def signature(self):
        creators = None
        if self.creators:
            creators = [c.first_name.strip().capitalize() for c in self.creators]
            creators = ', '.join(creators)
        if creators:
            return 'By %s' % creators
        return ''

    @property
    def signature_link(self):
        creators = None
        if self.creators:
            creators = [c.create_link() for c in self.creators]
            creators = ' '.join(creators)
        if creators:
            return 'By %s' % creators
        return ''

    @property
    def display_title(self):
        return "%s %s" % (self.title, self.signature)

    @property
    def display_title_link(self):
        return "%s %s" % (self.title, self.signature_link)

    def save(self, skip_auth=False, safe=True):
        """Set level based on creators"""
        if not self.level:
            levels = [m.next_level(save=False) for m in self.creators]
            self.level = LevelManaged.get_min_level([self.level] + levels)
        CurriculumElementMixin.save(self, skip_auth=skip_auth)

        # This is for re-synching with Elastic Search so it can be displayed in the
        # wonderwall. remove it first if necessary, and then apply it.
        self.update_es()

    def update_es(self):
        doc = ProjectDocument(self)
        doc.withdraw_unlinked_videos()
        doc.withdraw()
        doc.deploy()

    def delete(self):
        if self.parent_sku != 0:
            parent_project = Project.objects(sku=self.parent_sku)
            if parent_project.count() > 0:
                parent_project = list(parent_project)[0]
                parent_project.copy_count -= 1
                parent_project.save()
        super(Project, self).delete()

    def to_json(self):
        data = self
        res = {
            "id": data.id,
            "sku": data.sku,
            "title": data.title,
            "display_title": data.display_title,
            "status": data.status,
            "description": data.description,
            "level": data.level,
            "category": data.category,
            "difficulty": data.difficulty,
            "detail_link": data.detail_link,
            "purpose": data.purpose,
            "_options": {
                "category": self.CATEGORIES,
                "difficulty": self.DIFFICULTIES,
                "level": [l for l in sorted(LEVEL_COLOR_MAP, key=lambda x: LEVEL_COLOR_MAP[x][1]) if l != 'Novice']
            },

            "components": [item.to_json() for item in data.components],
            "files": [item.to_json() for item in data.files],
            "creators": [item.to_json() for item in data.creators],
            "tags": data.tags or [],
            "requirements": data.get_requirements()
        }

        return res

    def get_all_tags(self):
        total_tags = []
        results = self.objects(skip_auth=True).filter(and_(Project.tags.__ne__('{}'), Project.tags.__ne__('{""}')))
        for r in results:
            total_tags = total_tags + r.tags
        return list(set(map(str, total_tags)))
